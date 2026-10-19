# VELTOR stories

Автоматическая сборка Instagram-сторис из постов темы «Мото» в Telegram-группе
@koreamotocycles_veltor по утверждённому шаблону.

- Каждые 2 часа GitHub Actions забирает новые посты через бота, берёт первое фото
  альбома и 5 строк (модель, год, пробег, цена) и собирает сторис 1080×1920.
- Готовые сторис лежат в `stories/`, список — в `queue.json`.
- Claude по расписанию отправляет новые сторис в Metricool как Story с
  уведомлением на телефон; музыку добавляете вручную при публикации.

Токен бота хранится в Settings → Secrets and variables → Actions →
`TELEGRAM_BOT_TOKEN` и в репозитории не виден.

Шрифты: Inter (SIL Open Font License) и TeX Gyre Heros (GUST Font License), см. `fonts/`.
