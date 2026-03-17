# PILOT_REPO_REGISTRY

## Purpose
Pinned open-source repository set for V1 pilot validation of Operating-Pack Builder.

## Snapshot
- Created at: 2026-03-17
- Source: GitHub
- Pinning method: `git ls-remote <repo> HEAD`
- Rule: use fixed commit SHA only (never floating branch for pilot metrics)

## Coverage target
- Python: 3
- Node/TypeScript: 3
- Go: 2
- Mixed/Monorepo: 2
- Low-doc quality stress cases: 2

## Pilot set (12 repositories)

| ID | Category | Repository | Fixed SHA | Notes |
|---|---|---|---|---|
| PY-01 | python | https://github.com/pallets/flask | `4cae5d8e411b1e69949d8fae669afeacbd3e5908` | Mature Python web framework |
| PY-02 | python | https://github.com/fastapi/fastapi | `0127069d47b54aedb179931a862036f0a49c7554` | Async API framework |
| PY-03 | python | https://github.com/psf/requests | `0e4ae38f0c93d4f92a96c774bd52c069d12a4798` | Popular Python library |
| ND-01 | node | https://github.com/expressjs/express | `6c4249feec8ab40631817c8e7001baf2ed022224` | JS service framework |
| ND-02 | ts | https://github.com/nestjs/nest | `5a05f52c4368157219ea15c30ba881d9ddd64bd9` | TS backend framework |
| ND-03 | ts/monorepo | https://github.com/vercel/next.js | `862f9b9bb41d235e0d8cf44aa811e7fd118cee2a` | Large TS monorepo |
| GO-01 | go | https://github.com/gin-gonic/gin | `d3ffc9985281dcf4d3bef604cce4e662b1a327a6` | Go web framework |
| GO-02 | go | https://github.com/spf13/cobra | `61968e893eee2f27696c2fbc8e34fa5c4afaf7c4` | Go CLI framework |
| MX-01 | mixed/monorepo | https://github.com/kubernetes/kubernetes | `5edaecfa530b4424b5a712ab09ff2538cbd7c887` | Very large infra monorepo |
| MX-02 | mixed/monorepo | https://github.com/supabase/supabase | `e8b5b565a9b45dc2480b1e892c552b24a9498c93` | Product monorepo (web + infra + sql) |
| LD-01 | low-doc stress | https://github.com/fogleman/primitive | `0373c216458be1c4b40655b796a3aefedf8b7d23` | Smaller repo, low docs depth |
| LD-02 | low-doc stress | https://github.com/benhoyt/inih | `577ae2dee1f0d9c2d11c7f10375c1715f3d6940c` | Small config parser repo |

## Selection notes
- This set is intentionally mixed by scale and structure.
- `MX-*` and `LD-*` are expected to reveal edge failures in scanner/questionnaire/validator.
- Re-pin SHA periodically (weekly or before formal benchmark rerun).

## Clone and pin pattern

```powershell
git clone <repo-url>
cd <repo-folder>
git checkout <fixed-sha>
```
