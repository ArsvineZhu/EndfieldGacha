# Server Package AGENTS

**Updated:** 2026-05-26

Flask web server package for Endfield Gacha.

## File map

| File | Purpose |
|---|---|
| `app.py` | `create_app(dev_mode=False)` and `compress_static_files()` |
| `routes.py` | `create_routes(app)` registers the HTTP endpoints |
| `user.py` | User creation, loading, saving, and reset helpers |
| `resource.py` | Recharge, exchange, and resource consumption helpers |

## Current implementation facts

- The web app is built through the `server` package, not through `app/`
- User IDs are generated from IP + User-Agent via MD5
- User data is stored in SQLite `userdata.db`
- The runtime configuration is hard-wired to `configs/config_1`
- `POST /api/gacha` supports `pool_type` values `char` and `weapon`
- Character draws accept `count` values 1 or 10
- Weapon issues are fixed 10-pull applications and ignore the request count as a free-form size
- `POST /api/urgent_recruitment` consumes `urgent_recruitment`
- Recharge only accepts `6 / 30 / 98 / 198 / 328 / 648`
- Exchange only supports `origeometry -> oroberyl` and `origeometry -> arsenal_tickets`

## Notes

- Character draws update collection counts and award Arsenal Tickets
- Weapon issues update weapon collection counts and award AIC Quota
- The current code does not implement a separate duplicate-token exchange system

