# Firefox Bridge

Управление уже запущенным Firefox по TCP на `127.0.0.1:47221`. Порт слушает native host: Firefox сам запускает его, когда расширение вызывает `connectNative`. Снаружи только TCP, кадр stdin/stdout — внутренний протокол Firefox.

Это не WebDriver и не Marionette. `navigator.webdriver` не выставляется. Расширение не вставляет ничего в DOM страницы и не отдаёт ей свои ресурсы.

## Установка

Нужен `python3` в `PATH`, который видит Firefox, запущенный из Dock. Обычно это `/usr/bin/python3`, а не Homebrew и не pyenv.

### 1. Native host

Из корня репозитория:

```bash
python3 firefox_bridge/host/install_host.py
```

Скрипт делает `firefox_bridge_host.py` исполняемым и пишет манифест:

`~/Library/Application Support/Mozilla/NativeMessagingHosts/com.tortobaza.firefox_bridge.json`

### 2. Расширение в уже запущенный Firefox

1. Открыть `about:debugging#/runtime/this-firefox`.
2. Load Temporary Add-on.
3. Выбрать `firefox_bridge/extension/manifest.json`.

Сначала host, потом расширение. Если расширение уже было загружено, на этой же странице нажать Reload.

Временное расширение снимается при полном выходе из Firefox. В Release Firefox неподписанное расширение нельзя поставить постоянно.

Чтобы пережило перезапуск, нужен Firefox Developer Edition:

1. В `about:config` выставить `xpinstall.signatures.required` в `false`.
2. Собрать xpi (manifest должен лежать в корне архива):

```bash
cd firefox_bridge/extension
zip -r ../firefox-bridge.xpi manifest.json background.js
```

3. `about:addons` → шестерёнка → Install Add-on From File → `firefox_bridge/firefox-bridge.xpi`.

### 3. Проверка

Порт есть только пока Firefox запущен и расширение подключено. Адрес именно `127.0.0.1`: `localhost` на macOS может уйти в IPv6.

```bash
nc 127.0.0.1 47221
{"id":"1","method":"tabs.list","params":{}}
```

Строка должна заканчиваться переводом строки. В ответ придёт одна JSON-строка. Логи host пишутся в stderr и видны в Inspect у расширения на `about:debugging`.

Любой локальный процесс, который может открыть этот порт, управляет этим Firefox.

## Протокол

Одно JSON-сообщение на строку, UTF-8.

Запрос:

```json
{"id":"1","method":"tabs.create","params":{"url":"https://www.threads.net/","active":true}}
```

Успех: `{"id":"1","ok":true,"result":{...}}`

Ошибка: `{"id":"1","ok":false,"error":"..."}`

Невалидный JSON не рвёт слушатель: в сокет уходит `{"ok":false,"error":"invalid json"}`. Обрыв клиента тоже не останавливает порт.

Команды идут в расширение по одной. Пока расширение не прислало `ready`, соединение принимается, команда ждёт.

Лимит сообщения native messaging — 1 МБ. Если ответ не влезает, будет `ok: false`, `error: "native messaging limit exceeded"` и `size` в байтах, без обрезки.

| method | params | result |
| --- | --- | --- |
| `ping` | — | `{pong: true}` |
| `tabs.list` | — | список вкладок: `id`, `windowId`, `active`, `url`, `title`, `status`, `index` |
| `tabs.create` | `url`, `active` | вкладка |
| `tabs.close` | `tabId` | `{}` |
| `tabs.activate` | `tabId` | вкладка |
| `tabs.navigate` | `tabId`, `url` | вкладка |
| `tabs.reload` | `tabId` | `{}` |
| `tabs.wait` | `tabId`, `timeoutMs` | `{}` когда `status == complete`, иначе error `timeout` |
| `tabs.content` | `tabId`, `format` (`html` или `text`), `timeoutMs` | `{format, content}` главного фрейма. `html` — `document.documentElement.outerHTML`, `text` — `document.body.innerText` |
| `tabs.evaluate` | `tabId`, `expression`, `timeoutMs` | `{value}` результата выражения в изолированном мире главного фрейма |

`tabs.content` и `tabs.evaluate` сначала ждут полной загрузки, как `tabs.wait`.
