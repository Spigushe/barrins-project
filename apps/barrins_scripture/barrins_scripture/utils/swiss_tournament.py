def get_num_rounds(players_qty: int) -> int:
    if players_qty <= 8:
        return 0  # single elimination
    elif players_qty <= 32:
        return 5
    elif players_qty <= 64:
        return 6
    elif players_qty <= 128:
        return 7
    elif players_qty <= 226:
        return 8
    elif players_qty <= 409:
        return 9
    else:
        return 10
