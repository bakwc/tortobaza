#!/usr/bin/env python3
import datetime
import json
import os
import random
import socket
import ssl
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

HOST = "127.0.0.1"
PORT = 47221
QUERIES = ["батуми торт", "бенто батуми"]
NETWORK = "threads"
INGEST_URL = "https://sweet-chill.ge/api/social/messages/"
PROCESS_URL = "https://sweet-chill.ge/api/social/networks/threads/process-leads/?potential=true"
POTENTIAL_URL = "https://sweet-chill.ge/api/social/networks/threads/potential-leads/"
CONTEXT_URL = "https://sweet-chill.ge/api/social/messages/{}/context/"
VERIFY_URL = "https://sweet-chill.ge/api/social/networks/threads/verify-leads/"
PROFILE_URL = "https://www.threads.com/@{}"
ERROR_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
RESTART_SLEEP_S = 60
SSL_CONTEXT = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
POST_LIMIT = 50
LIGHT_POST_LIMIT = 38
PROFILE_POST_LIMIT = 20
TIMEOUT_MS = 30000
SERVER_TIMEOUT_S = 30
SERVER_RETRY_LIMIT = 30
SERVER_RETRY_SLEEP_S = 20
POLL_S = 0.5
POLL_DEADLINE_S = 30
SCROLL_MIN = 540
SCROLL_MAX = 1440
PAUSE_MIN = 1
PAUSE_MAX = 5
COUNT_EXPRESSION = """(() => document.querySelectorAll('a[href*="/post/"] time[datetime]').length)()"""
EXTRACT_EXPRESSION = """(() => {
  const CARD = '[data-pressable-container="true"]';
  const seen = new Set();
  const posts = [];
  for (const link of document.querySelectorAll('a[href*="/post/"]')) {
    const time = link.querySelector("time[datetime]");
    if (!time) {
      continue;
    }
    const card = link.closest(CARD);
    if (!card || card.parentElement.closest(CARD)) {
      continue;
    }
    const url = new URL(link.getAttribute("href"), location.origin).href;
    if (seen.has(url)) {
      continue;
    }
    seen.add(url);
    const username = new URL(url).pathname.split("/")[1].slice(1);
    const author = [...card.querySelectorAll('a[href="/@' + username + '"]')].find(
      (node) => node.closest(CARD) === card,
    );
    let header = link;
    while (!header.contains(author)) {
      header = header.parentElement;
    }
    const tag = header.querySelector('a[href*="serp_type=tags"]');
    const place = [...card.querySelectorAll('a[href*="serp_type=location_tag"]')].find(
      (node) => node.closest(CARD) === card,
    );
    const lines = [];
    for (const span of card.querySelectorAll('span[dir="auto"]')) {
      if (
        span.closest(CARD) !== card ||
        header.contains(span) ||
        span.parentElement.closest('span[dir="auto"], a, button, [role="button"]')
      ) {
        continue;
      }
      let value = "";
      const walker = document.createTreeWalker(span, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const parent = walker.currentNode.parentElement;
        const box = parent.closest("div");
        if (box && span.contains(box) && !parent.closest("a")) {
          continue;
        }
        value += walker.currentNode.textContent;
      }
      value = value.trim();
      if (value) {
        lines.push(value);
      }
    }
    posts.push({
      username: username,
      location: place ? place.innerText.trim() : "",
      topic: tag ? tag.innerText.trim() : "",
      text: lines.join("\\n"),
      datetime: time.getAttribute("datetime"),
      url: url,
    });
  }
  return posts;
})()"""
PROFILE_EXPRESSION = """(() => {
  const title = document.querySelector('meta[property="og:title"]');
  const description = document.querySelector('meta[property="og:description"]');
  return {
    title: title ? title.getAttribute("content").trim() : "",
    description: description ? description.getAttribute("content").trim() : "",
  };
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


def take(posts, seen, found, limit):
    added = False
    for post in found:
        if post["url"] in seen:
            continue
        seen.add(post["url"])
        posts.append(post)
        added = True
        if len(posts) == limit:
            break
    return added


def log(message):
    print(message, file=sys.stderr, flush=True)


def log_error(error):
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    with open(ERROR_LOG, "a", encoding="utf-8") as handle:
        handle.write(f"\n{stamp}\n")
        traceback.print_exception(type(error), error, error.__traceback__, file=handle)
    log(f"ошибка {error}")


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
    now = datetime.datetime.now(datetime.timezone.utc)
    day = now.date()
    if now.hour < 1:
        day = day - datetime.timedelta(days=1)
    return day


def search_url(query, day, recent: bool):
    params = {
        "after_date": day.isoformat(),
        "q": query,
        "serp_type": "default",
    }
    if recent:
        params["exact_match"] = "false"
        params["filter"] = "recent"
    return "https://www.threads.com/search?" + urllib.parse.urlencode(
        params,
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


def message_body(post, query):
    return {
        "source_key": query,
        "source_title": query,
        "external_id": external_id(post["url"]),
        "url": post["url"],
        "text": post["text"],
        "sent_at": post["datetime"],
        "sender_id": "",
        "sender_username": post["username"],
        "location": post["location"],
        "topic": post["topic"],
    }


def read_http(request):
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(
                request,
                context=SSL_CONTEXT,
                timeout=SERVER_TIMEOUT_S,
            ) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            if error.code != 500 or attempt == SERVER_RETRY_LIMIT:
                raise
            error.close()
            attempt += 1
            log(f"500 {request.full_url} повтор {attempt}")
            time.sleep(SERVER_RETRY_SLEEP_S)
            continue
        except urllib.error.URLError as error:
            if not isinstance(error.reason, TimeoutError) or attempt == SERVER_RETRY_LIMIT:
                raise
        except TimeoutError:
            if attempt == SERVER_RETRY_LIMIT:
                raise
        attempt += 1
        log(f"timeout {request.full_url} повтор {attempt}")


def get_json(url, token):
    request = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + token},
        method="GET",
    )
    status, raw = read_http(request)
    if status != 200:
        raise RuntimeError(f"get {status}")
    return json.loads(raw.decode("utf-8"))


def post_json(url, token, body):
    headers = {"Authorization": "Bearer " + token}
    payload = b""
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    return read_http(request)


def send_batch(token, items):
    status, raw = post_json(
        INGEST_URL,
        token,
        {
            "network": NETWORK,
            "messages": [message_body(post, query) for post, query in items],
        },
    )
    if status != 200:
        raise RuntimeError(f"ingest {status}")
    payload = json.loads(raw.decode("utf-8"))
    log(f"ingest {status} created {payload['created']} skipped {payload['skipped']}")


def process_leads(token):
    log("process-leads")
    status, _raw = post_json(PROCESS_URL, token, None)
    if status != 204:
        raise RuntimeError(f"process {status}")
    log(f"process-leads {status}")


def potential_leads(token):
    return get_json(POTENTIAL_URL, token)


def send_context(token, message_id, context, profile):
    status, _raw = post_json(
        CONTEXT_URL.format(message_id),
        token,
        {"context": context, "profile": profile},
    )
    if status != 204:
        raise RuntimeError(f"context {status}")
    log(f"context {message_id} {status}")


def verify_leads(token):
    log("verify-leads")
    status, _raw = post_json(VERIFY_URL, token, None)
    if status != 204:
        raise RuntimeError(f"verify {status}")
    log(f"verify-leads {status}")


def load_tab(conn, buffer, counter, url, label, run):
    while True:
        log(f"{label} {url}")
        created = call(conn, buffer, counter, "tabs.create", {"url": url, "active": True})
        tab_id = created["id"]
        try:
            return run(tab_id)
        except RuntimeError as error:
            if str(error) != "timeout":
                raise
            close_tab(conn, buffer, counter, tab_id)
            log(f"таймаут {url}")


def collect(conn, buffer, counter, url, limit):
    def run(tab_id):
        return collect_posts(conn, buffer, counter, tab_id, limit)

    return load_tab(conn, buffer, counter, url, "вкладка", run)


def collect_posts(conn, buffer, counter, tab_id, limit):
    deadline = time.monotonic() + POLL_DEADLINE_S
    count = 0
    while count == 0:
        if time.monotonic() >= deadline:
            log("постов нет")
            return tab_id, []
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
    take(posts, seen, result["value"], limit)
    report(len(posts))
    stuck = 0
    while len(posts) < limit:
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
        added = take(posts, seen, result["value"], limit)
        report(len(posts))
        if moved["value"] or added:
            stuck = 0
            continue
        stuck += 1
        if stuck == 2:
            log("лента остановилась")
            break
    return tab_id, posts


def collect_context(conn, buffer, counter, url):
    def run(tab_id):
        deadline = time.monotonic() + POLL_DEADLINE_S
        count = 0
        while count == 0:
            if time.monotonic() >= deadline:
                log("постов нет")
                close_tab(conn, buffer, counter, tab_id)
                return []
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
        close_tab(conn, buffer, counter, tab_id)
        return [
            {
                "username": post["username"],
                "text": post["text"],
                "sent_at": post["datetime"],
                "url": post["url"],
            }
            for post in result["value"]
        ]

    return load_tab(conn, buffer, counter, url, "контекст", run)


def profile_posts(found, username):
    posts = []
    for post in found:
        if post["username"] != username:
            continue
        posts.append(
            {
                "text": post["text"],
                "sent_at": post["datetime"],
                "url": post["url"],
            }
        )
        if len(posts) == PROFILE_POST_LIMIT:
            break
    return posts


def read_profile(conn, buffer, counter, tab_id):
    result = call(
        conn,
        buffer,
        counter,
        "tabs.evaluate",
        {
            "tabId": tab_id,
            "expression": PROFILE_EXPRESSION,
            "timeoutMs": TIMEOUT_MS,
        },
    )
    return result["value"]


def collect_profile(conn, buffer, counter, username):
    url = PROFILE_URL.format(username)

    def run(tab_id):
        deadline = time.monotonic() + POLL_DEADLINE_S
        count = 0
        while count == 0:
            if time.monotonic() >= deadline:
                log("постов нет")
                profile = read_profile(conn, buffer, counter, tab_id)
                close_tab(conn, buffer, counter, tab_id)
                return {
                    "title": profile["title"],
                    "description": profile["description"],
                    "posts": [],
                }
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
        profile = read_profile(conn, buffer, counter, tab_id)
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
        close_tab(conn, buffer, counter, tab_id)
        return {
            "title": profile["title"],
            "description": profile["description"],
            "posts": profile_posts(result["value"], username),
        }

    return load_tab(conn, buffer, counter, url, "профиль", run)


def close_tab(conn, buffer, counter, tab_id):
    call(conn, buffer, counter, "tabs.close", {"tabId": tab_id})
    log(f"вкладка закрыта {tab_id}")


def run_cycle(conn, buffer, counter, token, queries, limit, kind, recent: bool):
    day = search_day()
    log(f"{kind} {day.isoformat()}")
    sent = set()
    batch = []
    for query in queries:
        log(f"поиск {query}")
        tab_id, posts = collect(conn, buffer, counter, search_url(query, day, recent), limit)
        for post in posts:
            if post["url"] in sent:
                log(f"уже был {post['url']}")
                continue
            sent.add(post["url"])
            batch.append((post, query))
        close_tab(conn, buffer, counter, tab_id)
    send_batch(token, batch)
    process_leads(token)
    for lead in potential_leads(token):
        context = collect_context(conn, buffer, counter, lead["url"])
        profile = collect_profile(conn, buffer, counter, lead["sender_username"])
        send_context(token, lead["id"], context, profile)
        time.sleep(random.uniform(PAUSE_MIN, PAUSE_MAX))
    verify_leads(token)


def cycle_pause():
    pause = random.uniform(150, 210)
    log(f"сон {round(pause)} с")
    time.sleep(pause)


def run_forever(token):
    conn = socket.create_connection((HOST, PORT))
    buffer = bytearray()
    counter = [1]
    while True:
        run_cycle(conn, buffer, counter, token, QUERIES, POST_LIMIT, "тяжёлый", False)
        for _ in range(random.randint(2, 3)):
            cycle_pause()
            run_cycle(
                conn,
                buffer,
                counter,
                token,
                ["батуми"],
                LIGHT_POST_LIMIT,
                "лёгкий",
                True,
            )
        cycle_pause()


def main():
    token = os.environ["SOCIAL_INGEST_TOKEN"]
    while True:
        try:
            run_forever(token)
        except Exception as error:
            log_error(error)
            time.sleep(RESTART_SLEEP_S)


if __name__ == "__main__":
    main()
