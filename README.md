# Telegram PiVPN Manager

Решение для удаленного администрирования VPN(pivpn) сервера на WireGuard через Telegram. Делал под себя, а то лень каждый раз в ssh лезть, а с телефона не всегда удобно это делать. 
Тестировал на Ubuntu 24.04.

## Функциональные возможности

*   **VPN:** Генерация `.conf` и QR-кодов, удаление клиентов, проверка статуса Handshake (Online/Offline).
*   **Мониторинг:** Сбор метрик CPU (с построением графика), RAM, Disk, Network.
*   **Безопасность:** Парсинг `/var/log/auth.log` на предмет успешных SSH-авторизаций.
*   **Обслуживание:** Управление системной службой (reboot), очистка кэша пакетов.

## Стек технологий

*   **Language:** Python 3.8+
*   **Libraries:** `aiogram` (v3.x), `psutil`, `apscheduler`, `matplotlib`.
*   **System Tools:** `pivpn` (WireGuard), `qrencode`, `systemd`.

## Установка

### 1. Подготовка VPN-среды
Перед установкой бота в системе должен быть развернут PiVPN:
```bash
curl -L https://install.pivpn.io | bash
```

### 2. Развертывание бота
Поместите файлы `bot.py` и `install_bot.py` в одну директорию на целевом сервере.

### 3. Автоматизированная настройка
Запустите скрипт инициализации с правами суперпользователя:
```bash
sudo python3 install_bot.py
```
В ходе выполнения скрипта необходимо будет ввести:
*   `API Token` — токен бота из BotFather.
*   `User ID` — числовой идентификатор владельца для ограничения доступа.

**Скрипт автоматически выполнит:**
1. Инсталляцию системных зависимостей (`python3-pip`, `qrencode`, `python3-matplotlib`).
2. Установку Python-пакетов через `pip`.
3. Патчинг путей и переменных окружения внутри `bot.py` под текущую директорию.
4. Регистрацию и запуск юнита `vpn-bot.service` в `systemd`.

## Интерфейс управления


| Команда | Системное действие |
| :--- | :--- |
| `📊 Статус` | `psutil.cpu_percent` + `matplotlib` render |
| `👥 Список` | `pivpn list` + `wg show latest-handshake` |
| `➕ Создать` | `pivpn add -n` + `qrencode` |
| `❌ Удалить` | `pivpn -r -y` |
| `🧹 Очистка` | `apt clean && apt autoremove` |
| `🔄 Ребут` | `/sbin/reboot` |

## Администрирование службы

*   **Перезапуск:** `sudo systemctl restart vpn-bot.service`
*   **Просмотр логов:** `sudo journalctl -u vpn-bot.service -f`
*   **Конфигурационный файл:** Автоматически создается в `config_data.py`.
