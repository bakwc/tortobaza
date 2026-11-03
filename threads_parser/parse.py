#!/usr/bin/env python3
import datetime
import json
import os
import random
import socket
import sys
import time
import urllib.parse
import urllib.request

HOST = "127.0.0.1"
PORT = 47221
QUERIES = ["батуми торт", "бенто батуми"]
NETWORK = "threads"
INGEST_URL = "https://sweet-chill.ge/api/social/messages/"
PROCESS_URL = "https://sweet-chill.ge/api/social/networks/threads/process-leads/"
POST_LIMIT = 50
TIMEOUT_MS = 30000
POLL_S = 0.5
POLL_DEADLINE_S = 30
SCROLL_MIN = 540
SCROLL_MAX = 1440
PAUSE_MIN = 1
PAUSE_MAX = 5
COUNT_EXPRESSION = """(() => document.querySelectorAll('a[href*="/post/"] time[datetime]').length)()"""
EXTRACT_EXPRESSION = """(() => {
  const seen = new Set();
  const posts = [];
  const links = document.querySelectorAll('a[href*="/post/"]');
  for (const link of links) {
    const time = link.querySelector("time[datetime]");
    if (!time) {
      continue;
    }
    const card = link.closest('[data-pressable-container="true"]');
    if (!card) {
      continue;
    }
    const url = new URL(link.getAttribute("href"), location.origin).href;
    if (seen.has(url)) {
      continue;
    }
    seen.add(url);
    let username = "";
    const authors = card.querySelectorAll('a[href^="/@"]');
    for (const author of authors) {
      if (author.closest('[data-pressable-container="true"]') !== card) {
        continue;
      }
      const path = author.getAttribute("href").split("?")[0];
      const parts = path.split("/").filter(Boolean);
      if (parts.length === 1 && parts[0].startsWith("@")) {
        username = parts[0].slice(1);
        break;
      }
    }
    const texts = [];
    const nodes = card.querySelectorAll('span[dir="auto"], div[dir="auto"]');
    for (const node of nodes) {
      if (node.closest('[data-pressable-container="true"]') !== card) {
        continue;
      }
      const parent = node.parentElement;
      if (
        parent &&
        parent.matches('span[dir="auto"], div[dir="auto"]') &&
        parent.closest('[data-pressable-container="true"]') === card
      ) {
        continue;
      }
      const value = node.innerText.trim();
      if (!value || texts[texts.length - 1] === value) {
        continue;
      }
      texts.push(value);
    }
    posts.push({
      username: username,
      text: texts.join("\\n"),
      datetime: time.getAttribute("datetime"),
      url: url,
    });
  }
  return posts;
})()"""


def read_line(conn, buffer):
    while b"\n" not in buffer:
        chunk = conn.recv(65536)
        if not chunk:
            raise ConnectionError("bridge closed")
        buffer.extend(chunk)
    line, _, rest = buffer.partition(b"\n")
    buffer.clear()
    buffer.extend(rest)
    return json.loads(line.decode("utf-8"))


def scroll_expression(distance, duration):
    return (
        "(() => {"
        f" const distance = {distance};"
        f" const duration = {duration};"
        " const start = window.scrollY;"
        " const t0 = performance.now();"
        " return new Promise((resolve) => {"
        " function frame(now) {"
        " const t = Math.min(1, (now - t0) / duration);"
        " const eased = t < 0.5 ? 2 * t * t : 1 - ((-2 * t + 2) ** 2) / 2;"
        " window.scrollTo(0, start + distance * eased);"
        " if (t < 1) { requestAnimationFrame(frame); return; }"
        " resolve(window.scrollY > start);"
        " }"
        " requestAnimationFrame(frame);"
        " });"
        "})()"
    )


def take(posts, seen, found):
    added = False
    for post in found:
        if post["url"] in seen:
            continue
        seen.add(post["url"])
        posts.append(post)
        added = True
        if len(posts) == POST_LIMIT:
            break
    return added


def log(message):
    print(message, file=sys.stderr, flush=True)


def report(count):
    log(f"найдено {count}")


def call(conn, buffer, counter, method, params):
    request_id = str(counter[0])
    counter[0] += 1
    payload = {"id": request_id, "method": method, "params": params}
    conn.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")
    response = read_line(conn, buffer)
    if not response["ok"]:
        raise RuntimeError(response["error"])
    return response["result"]


def search_day():
    now = datetime.datetime.now().astimezone()
    day = now.date()
    if now.hour < 1:
        day = day - datetime.timedelta(days=1)
    return day


def search_url(query, day):
    return "https://www.threads.com/search?" + urllib.parse.urlencode(
        {
            "after_date": day.isoformat(),
            "q": query,
            "serp_type": "default",
        },
        quote_via=urllib.parse.quote,
    )


def external_id(url):
    path = urllib.parse.urlparse(url).path
    marker = "/post/"
    index = path.find(marker)
    if index < 0:
        raise RuntimeError(url)
    value = path[index + len(marker) :].strip("/")
    if value == "":
        raise RuntimeError(url)
    return value


def message_body(post):
    username = post["username"]
    return {
        "network": NETWORK,
        "source_key": username,
        "source_title": username,
        "external_id": external_id(post["url"]),
        "url": post["url"],
        "text": post["text"],
        "sent_at": post["datetime"],
        "sender_id": "",
        "sender_username": username,
    }


def post_json(url, token, body):
    headers = {"Authorization": "Bearer " + token}
    payload = b""
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request) as response:
        status = response.status
        response.read()
    return status


def send_message(token, post):
    status = post_json(INGEST_URL, token, message_body(post))
    if status != 200 and status != 201:
        raise RuntimeError(f"ingest {status}")
    log(f"ingest {status} {post['url']}")


def process_leads(token):
    log("process-leads")
    status = post_json(PROCESS_URL, token, None)
    if status != 204:
        raise RuntimeError(f"process {status}")
    log(f"process-leads {status}")


def collect(conn, buffer, counter, url):
    log(f"вкладка {url}")
    created = call(conn, buffer, counter, "tabs.create", {"url": url, "active": True})
    tab_id = created["id"]
    deadline = time.monotonic() + POLL_DEADLINE_S
    count = 0
    while count == 0:
        if time.monotonic() >= deadline:
            raise RuntimeError("no posts")
        result = call(
            conn,
            buffer,
            counter,
            "tabs.evaluate",
            {
                "tabId": tab_id,
                "expression": COUNT_EXPRESSION,
                "timeoutMs": TIMEOUT_MS,
            },
        )
        count = result["value"]
        if count == 0:
            time.sleep(POLL_S)
    posts = []
    seen = set()
    result = call(
        conn,
        buffer,
        counter,
        "tabs.evaluate",
        {
            "tabId": tab_id,
            "expression": EXTRACT_EXPRESSION,
            "timeoutMs": TIMEOUT_MS,
        },
    )
    take(posts, seen, result["value"])
    report(len(posts))
    stuck = 0
    while len(posts) < POST_LIMIT:
        time.sleep(random.uniform(PAUSE_MIN, PAUSE_MAX))
        moved = call(
            conn,
            buffer,
            counter,
            "tabs.evaluate",
            {
                "tabId": tab_id,
                "expression": scroll_expression(
                    random.randint(SCROLL_MIN, SCROLL_MAX),
                    random.randint(300, 1200),
                ),
                "timeoutMs": TIMEOUT_MS,
            },
        )
        result = call(
            conn,
            buffer,
            counter,
            "tabs.evaluate",
            {
                "tabId": tab_id,
                "expression": EXTRACT_EXPRESSION,
                "timeoutMs": TIMEOUT_MS,
            },
        )
        added = take(posts, seen, result["value"])
        report(len(posts))
        if moved["value"] or added:
            stuck = 0
            continue
        stuck += 1
        if stuck == 2:
            log("лента остановилась")
            break
    return tab_id, posts


def close_tab(conn, buffer, counter, tab_id):
    call(conn, buffer, counter, "tabs.close", {"tabId": tab_id})
    log(f"вкладка закрыта {tab_id}")


def main():
    token = os.environ["SOCIAL_INGEST_TOKEN"]
    conn = socket.create_connection((HOST, PORT))
    buffer = bytearray()
    counter = [1]
    while True:
        day = search_day()
        log(f"круг {day.isoformat()}")
        sent = set()
        for query in QUERIES:
            log(f"поиск {query}")
            tab_id, posts = collect(conn, buffer, counter, search_url(query, day))
            for post in posts:
                if post["url"] in sent:
                    log(f"уже был {post['url']}")
                    continue
                sent.add(post["url"])
                send_message(token, post)
            close_tab(conn, buffer, counter, tab_id)
        process_leads(token)
        pause = random.uniform(600, 780)
        log(f"сон {round(pause)} с")
        time.sleep(pause)


if __name__ == "__main__":
    main()
