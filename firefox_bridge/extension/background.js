const NATIVE_LIMIT = 1024 * 1024;
const NATIVE_HOST = "com.tortobaza.firefox_bridge";

function tabInfo(tab) {
  return {
    id: tab.id,
    windowId: tab.windowId,
    active: tab.active,
    url: tab.url,
    title: tab.title,
    status: tab.status,
    index: tab.index,
  };
}

function requireParam(params, name) {
  if (params === undefined || params === null || params[name] === undefined || params[name] === null) {
    throw new Error(name + " is required");
  }
}

function scriptable(url) {
  return typeof url === "string" && (url.startsWith("http://") || url.startsWith("https://"));
}

function waitForTab(tabId, timeoutMs) {
  return new Promise((resolve, reject) => {
    let settled = false;

    function settle(error) {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      browser.tabs.onUpdated.removeListener(onUpdated);
      if (error) {
        reject(error);
        return;
      }
      resolve();
    }

    function consider(tab) {
      if (tab.status === "complete" && scriptable(tab.url)) {
        settle(null);
      }
    }

    function onUpdated(id, info, tab) {
      if (id !== tabId) {
        return;
      }
      consider(tab);
    }

    const timer = setTimeout(() => {
      settle(new Error("timeout"));
    }, timeoutMs);
    browser.tabs.onUpdated.addListener(onUpdated);
    browser.tabs.get(tabId).then(consider, (error) => {
      settle(error);
    });
  });
}

function contentCode(format) {
  if (format === "html") {
    return "document.documentElement.outerHTML";
  }
  if (format === "text") {
    return "document.body.innerText";
  }
  throw new Error("format must be html or text");
}

async function dispatch(message) {
  const method = message.method;
  const params = message.params;
  if (method === "ping") {
    return { pong: true };
  }
  if (method === "tabs.list") {
    const tabs = await browser.tabs.query({});
    return tabs.map(tabInfo);
  }
  if (method === "tabs.create") {
    requireParam(params, "url");
    requireParam(params, "active");
    const tab = await browser.tabs.create({ url: params.url, active: params.active });
    return tabInfo(tab);
  }
  if (method === "tabs.close") {
    requireParam(params, "tabId");
    await browser.tabs.remove(params.tabId);
    return {};
  }
  if (method === "tabs.activate") {
    requireParam(params, "tabId");
    const tab = await browser.tabs.update(params.tabId, { active: true });
    return tabInfo(tab);
  }
  if (method === "tabs.navigate") {
    requireParam(params, "tabId");
    requireParam(params, "url");
    const tab = await browser.tabs.update(params.tabId, { url: params.url });
    return tabInfo(tab);
  }
  if (method === "tabs.reload") {
    requireParam(params, "tabId");
    await browser.tabs.reload(params.tabId);
    return {};
  }
  if (method === "tabs.wait") {
    requireParam(params, "tabId");
    requireParam(params, "timeoutMs");
    await waitForTab(params.tabId, params.timeoutMs);
    return {};
  }
  if (method === "tabs.content") {
    requireParam(params, "tabId");
    requireParam(params, "format");
    requireParam(params, "timeoutMs");
    await waitForTab(params.tabId, params.timeoutMs);
    const results = await browser.tabs.executeScript(params.tabId, { code: contentCode(params.format) });
    return { format: params.format, content: results[0] };
  }
  if (method === "tabs.evaluate") {
    requireParam(params, "tabId");
    requireParam(params, "expression");
    requireParam(params, "timeoutMs");
    await waitForTab(params.tabId, params.timeoutMs);
    const results = await browser.tabs.executeScript(params.tabId, { code: params.expression });
    return { value: results[0] };
  }
  throw new Error("unknown method");
}

function fit(message, response) {
  const size = new TextEncoder().encode(JSON.stringify(response)).length;
  if (size >= NATIVE_LIMIT) {
    return {
      id: message.id,
      ok: false,
      error: "native messaging limit exceeded",
      size: size,
    };
  }
  return response;
}

async function handle(message) {
  try {
    const result = await dispatch(message);
    return fit(message, { id: message.id, ok: true, result: result });
  } catch (error) {
    const response = {
      ok: false,
      error: error && error.message ? error.message : String(error),
    };
    if (message && Object.prototype.hasOwnProperty.call(message, "id")) {
      response.id = message.id;
    }
    return response;
  }
}

function connect() {
  const port = browser.runtime.connectNative(NATIVE_HOST);
  port.onMessage.addListener((message) => {
    handle(message).then((response) => {
      port.postMessage(response);
    });
  });
  port.onDisconnect.addListener((disconnected) => {
    console.error("native host disconnected", disconnected.error);
    setTimeout(connect, 1000);
  });
  port.postMessage({ type: "ready" });
}

connect();
