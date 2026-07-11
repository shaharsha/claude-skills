# Library icons

Real, recognizable icons (Postgres, React, Docker, AWS, databases, files…) via the
MCP — no image files, no manual steps. The trick: a community `.excalidrawlib` file
is just JSON of **standard Excalidraw elements**, so an icon's elements can be
extracted, rescaled, repositioned, and inserted with `edit_scene_content`.
`scripts/excalidraw_tools.py` automates the extraction; you insert and verify.

## Contents
- Why this works
- The workflow
- Identifying unnamed (v1) icons
- Recommended libraries
- Placing an icon in a card

## Why this works

There is no built-in icon set in Excalidraw, and the MCP can't embed images (a
strict CSP blocks external assets) or emoji in scene text. But the official
[excalidraw-libraries](https://github.com/excalidraw/excalidraw-libraries) catalog
(~230 packs) stores each pack as JSON whose items are ordinary elements — exactly
what `edit_scene_content` accepts. So "library icons" and "hand-drawn primitives"
are the same thing under the hood; a library just gives you a nicer pre-made one.

## The workflow

1. **Find a pack** for the icon you need:
   ```bash
   python scripts/excalidraw_tools.py catalog database postgres
   python scripts/excalidraw_tools.py catalog aws
   ```
   Prints matching `author/name.excalidrawlib` sources + descriptions.

2. **List its items** to get the index or name of the one you want:
   ```bash
   python scripts/excalidraw_tools.py list pclainchard/it-logos
   ```
   v2 packs have real item names (Python, React, Docker…); v1 packs are unnamed
   (`#0`, `#1`, …) — identify those visually (next section).

3. **Extract a positioned icon** as an add-payload:
   ```bash
   python scripts/excalidraw_tools.py icon pclainchard/it-logos \
       --item React --at 1080 190 --height 38
   ```
   `--at X Y` = horizontal **center** X, **top** Y; `--height` scales the whole icon
   (rotation-aware, so tilted geometry like the React atom scales correctly).
   `--swap OLD=NEW` replaces a text label baked into the icon (e.g. a JSON-file icon
   → `--swap JSON=CSV`). The script whitelists safe fields, drops `id`/`seed`/etc.,
   and maps legacy `draw`→`freedraw` and legacy font ids automatically.

4. **Insert** the printed JSON into an `edit_scene_content` `add` call. If the icon
   must sit above a filled card, give its elements a high `index` (see
   mcp-gotchas.md — z-order).

5. **Verify** with `take_screenshot` (icon shape/color render fine) and, if the icon
   contains text, `search_scene_content`.

## Identifying unnamed (v1) icons

v1 packs carry no names, and MCP screenshots don't render text, so identify by
shape: extract a handful of candidates into a **temp scene** in a row and
screenshot. Create the scene, add the candidates (space them ~300px apart), shoot,
read off which index is which, then `delete_scene` the temp scene. Don't guess from
the item's element histogram alone — e.g. in one pack the item that looked like a
database cylinder by name was actually a load balancer.

## Recommended libraries

These are just fast starting points — the `catalog` command searches **all ~230
packs live**, so you never need to bundle library data or memorize this list; if you
need something not here (Kafka, Snowflake, Terraform, networking, printers…), run
`catalog <keyword>` and it'll surface it.

| pack | contains |
|---|---|
| `pclainchard/it-logos` | Python, React, Docker, Kubernetes, VSCode, GitLab… (named) |
| `drwnio/drwnio` | database, Postgres, Redis, Nginx, RabbitMQ, JSON, docker (v1, unnamed) |
| `youritjang/software-architecture` | microservice, cache, event bus, database components |
| `rohanp/system-design`, `niknm/systemdesignicons` | generic system-design components |
| `kvchitrapu/data-sources` | APIs, protocols, USB, email, FTP, Kafka, GraphQL, databases |
| `finfin/flow-chart-symbols` | start/end, process, decision, document, multi-doc |
| `childishgirl/aws-architecture-icons` | **the AWS pack to reach for — 252 named items**: ECS, ECR, RDS, Fargate, Route 53, VPC, ALB/ELB, IAM (+Identity Center), ACM, Parameter Store, Secrets Manager, S3, CloudWatch, NAT gateway, Internet gateway, Organizations, Control Tower, GuardDuty, EC2… (`narhari-motivaras/aws-architecture-icons` has only ~4). `mguidoti/google-icons` = GCP/Workspace product icons; a plain GCP logo is `cloud/cloud` item 6 |
| `7demonsrising/azure-*` | Azure compute/storage/network/containers |
| `boemska-nik/kubernetes-icons`, `mattias-fjellstrom/hashicorp` | K8s / HashiCorp |

## When there's no library icon (brand logos, personas)

The ~230-pack catalog is deep on infra (AWS/GCP/Azure/K8s) but **thin on SaaS brand
logos and generic people/devices**. Confirmed absent: Auth0, GoDaddy, Railway, a
plain "Google Workspace" mark, and any clean laptop/user/browser icon. Don't spin
your wheels hunting — decide fast between a real logo and a drawn glyph.

- **You cannot embed an SVG/PNG through the MCP.** `read_excalidraw_format` defines
  no `image`/`fileId` element and the CSP blocks external assets — so there's no
  programmatic way to drop in a real logo file. (The Excalidraw *app* can paste/drag
  an image onto the canvas; offer that as a manual step if the user wants pixel-exact
  brand marks.)
- **A heavy real logo looks worse than a glyph at badge size.** Some lib logos are
  ~150–300 `freedraw` strokes (e.g. the GitHub octocat); scaled to a ~24px badge they
  turn into an illegible blob and bloat the scene. At small sizes, a clean 2–5
  element **drawn glyph** reads better than the "real" logo. Reserve real logos for
  ones that stay legible small (a simple colored mark like the GCP hexagon is fine).

**Fallback glyph recipes** (draw from primitives, colour with the box's border
accent, `roughness:0`, place as a small badge centered above the title or top-right
for dense boxes; make the box fill transparent so the glyph shows — see
`mcp-gotchas.md` z-order):

| glyph | build |
|---|---|
| laptop (person/client) | screen `rectangle` + wider thin base `rectangle` |
| cloud (Google/generic) | 3 overlapping **filled** `ellipse`s (stroke = fill, no inner lines) |
| lock (auth) | arch `line` (shackle) + rounded `rectangle` body + tiny keyhole `ellipse` |
| globe (domain/registrar) | `ellipse` + inner vertical `ellipse` (meridian) + horizontal `line` (equator) |
| shield (identity/IdP) | closed pentagon `line` + short checkmark `line` |
| git (repo/VCS) | vertical `line` + branch `line` + 3 small filled `ellipse` dots |
| rail/track (Railway) | 2 vertical `line`s + 3 short horizontal tie `line`s |

## Placing an icon in a card

To put an icon above a label, both centered as one block inside a card, first get
the two positions from the `place` subcommand, then extract the icon at the icon
position and add a standalone label at the label position:

```bash
python scripts/excalidraw_tools.py place --box 990 190 160 120 --icon-h 40 --font 18
# → icon: center_x, top_y ;  label: center_x, y
python scripts/excalidraw_tools.py icon <lib> --item <x> --at <icon.center_x> <icon.top_y> --height 40
```

Then add the standalone label at `label.center_x` / `label.y` with
`"textAlign":"center"`. A bound `label` won't work here — it's always vertically
centered in the shape (mcp-gotchas.md).
