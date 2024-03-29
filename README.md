![Docker](https://github.com/djoamersfoort/aanmelden/workflows/Docker/badge.svg)

# aanmelden
Site om leden te laten aanmelden

# API

De volgende API endpoints zijn aanwezig:

### /api/v2/free
Uitgebreide versie van de 'free' API.
Geeft per dagdeel het aantal vrije slots, aantal begeleiders, datum, tijden, etc. terug:

```json
[
  {
    "description": "Vrijdag (19:00 - 22:00)",
    "pod": "e",
    "name": "fri",
    "date": "2021-09-17",
    "closed": false,
    "available": 15,
    "taken": 1,
    "tutor_count": 4
  },
  {
    "description": "Zaterdag (09:30 - 13:30)",
    "pod": "m",
    "name": "sat",
    "date": "2021-09-18",
    "closed": false,
    "available": 13,
    "taken": 3,
    "tutor_count": 2
  }
]
```

### /api/v1/is_present/\<dag\>/\<pod\>/\<user_id\>
Geeft terug of een bepaald DJO lid op de opgegeven dag + dagdeel aangemeld is.
Voor dit endpoint is autorisatie nodig. In de Authorization header wordt een Bearer token
verwacht met grant_type 'client_credentials', waarvan het bijbehorende client_id is ge-whitelist
voor deze API. Bedoeld voor de Corveeapplicatie.

`dag` kan 'fri' of 'sat' zijn.

`pod` Dagdeel: kan 'm', 'a', of 'e' zijn (morning, afternoon, evening).

`user_id` is het IDP userid (idp-\<nummer\>) van het op te vragen DJO lid.
