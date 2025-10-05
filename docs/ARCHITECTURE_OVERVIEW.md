# AstroEngine High-Level Architecture

This document captures the current top-level service layout for AstroEngine, emphasizing the module → submodule → channel → subchannel boundaries that keep the astrology computation stack organized and upgrade-friendly. Each component corresponds to data-backed workflows that strictly source information from maintained datasets (Solar Fire exports, Swiss Ephemeris files, SQLite caches, and related rulesets) to preserve integrity across natal, mundane, and tracking contexts.

```plantuml
@startuml
skinparam shadowing false
skinparam componentStyle rectangle

actor User
actor "Streamlit UI" as UI
rectangle "AstroEngine" {
[Router /v1]
[Ephemeris Service]
[Cache Layer (LRU + Redis opt.)]
[DB Access Layer]
}
node "Storage" {
database "API DB (SQLite/Postgres)" as DB
collections "Positions Cache (SQLite)" as PC
folder "Swiss Ephemeris Files" as SE
}


User --> UI
UI --> API: HTTP (gzip, ETag)
API --> "Ephemeris Service": compute(range, bodies)
"Ephemeris Service" --> SE: read eph data
"Ephemeris Service" --> PC: read/write daily cache
"Ephemeris Service" --> "Cache Layer (LRU + Redis opt.)": in-proc hits
API --> DB: rulesets, versions
@enduml
```

The diagram distinguishes the request/response flow from the storage subsystems, showing how the ephemeris service mediates every calculation by pulling deterministic data from the indexed Swiss Ephemeris catalogues, cached daily positions, and the broader AstroEngine ruleset database. Modules and submodules expose channels and subchannels that feed this pipeline, ensuring any upgrades or new datasets slot into the hierarchy without displacing existing functionality.
