# Тестовое задание для grpc_udp_monitor

## Состав репозитория

- `cpp-application/` - тестируемое C++ приложение.
- `build.sh` - скрипт сборки C++ приложения в директорию `./build`.
- `test.sh` - скрипт запуска всех автотестов.
- `tests/` - набор black-box тестов на `pytest` (взаимодействие через gRPC и UDP).
- `requirements.txt` - Python-зависимости для тестовой инфраструктуры.
- `TESTPLAN.md` - тест-план, на основе которого реализованы автотесты.

## Подготовка окружения (Ubuntu 24.04+)

Установить системные зависимости:

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  cmake \
  pkg-config \
  ninja-build \
  protobuf-compiler \
  libprotobuf-dev \
  libgrpc++-dev \
  libgrpc-dev \
  libboost-system-dev \
  python3 \
  python3-pip \
  python3-venv
```

Создать виртуальное окружение и установить Python-зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Сборка и запуск тестов

```bash
./build.sh
./test.sh
```

## Проверка в Ubuntu (CI)

Для гарантированного прогона в целевом окружении добавлен workflow `GitHub Actions`:

- файл: `.github/workflows/ci.yml`;
- окружение: `ubuntu-24.04`;
- шаги: установка системных зависимостей, установка Python-зависимостей, `./build.sh`, `./test.sh`.

После первого push в репозиторий проверка автоматически запустится во вкладке `Actions`.

## Примечания по параметрам и допущениям

Все значения, связанные со временем ожидания, вынесены в `tests/config.py`:

- таймаут старта приложения;
- интервал опроса `IsReady`;
- таймаут ожидания обновления счетчиков после отправки UDP;
- таймаут корректного завершения процесса.

Такой подход упрощает поддержку тестов при изменении времени старта и поведения приложения.
