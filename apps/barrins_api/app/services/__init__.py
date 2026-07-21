"""Services package — business logic layer.

One module per domain, e.g.:

    app/services/card_service.py
    app/services/player_service.py
    app/services/tournament_service.py

Services receive a database session via dependency injection and own all
business logic. Routers call services; services call repositories or ORM
directly.
"""
