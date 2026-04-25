# DESIGN

## 1. Mục đích của tài liệu

`DESIGN.md` là nguồn mô tả **UI/UX + visual system + information architecture + interaction rules** của VoiceForge Studio.

Tài liệu này phục vụ 4 mục tiêu:

1. giúp team chỉnh giao diện mà không phải đọc hết code React
2. giữ thống nhất giữa product, design và engineering
3. làm chuẩn cho đa ngôn ngữ ngay từ đầu
4. tạo nền cho các flow phức tạp hơn về sau như voice cloning, presets, approval, collaboration

---

## 2. Product vision

VoiceForge Studio là **operator workspace cho voice generation**, không phải website giới thiệu và cũng không phải editor video.

Mọi quyết định UI phải ưu tiên các câu hỏi sau:
- đang làm project nào?
- đang dùng engine nào?
- voice nào phù hợp?
- cần chỉnh tham số gì?
- job đang ở trạng thái nào?
- audio đã sinh ra nằm ở đâu?
- có cảnh báo hoặc lỗi nào cần xử lý ngay không?

---

## 3. Design principles

### 3.1 Voice-first
Mọi màn hình phải phục vụ luồng:
**project → engine → voice → config → queue → monitor → result**

### 3.2 Project-first
Project là đơn vị tổ chức chính.
Không để voice, config, jobs, results bị tách rời không ngữ cảnh.

### 3.3 Progressive disclosure
- thao tác cơ bản phải nhanh, ít bước
- thao tác nâng cao chỉ hiện khi cần
- các setting theo provider phải được mở dần, không dồn tất cả vào một form

### 3.4 Large-context picking
Với nhiều engine TTS khác nhau, dropdown đơn giản là không đủ.
Bộ chọn voice phải đủ lớn để người dùng:
- nhìn được engine
- nhìn được locale/quốc gia khả dụng
- xem được danh sách voice
- biết có avatar hay không
- biết có nghe thử hay không
- biết voice có cloning / multilingual / realtime / expressive hay không

### 3.5 Realtime trust
UI phải có SSE/live updates để người dùng không phải F5.
Realtime áp dụng cho:
- jobs
- notifications
- event timeline
- project rollups cơ bản

### 3.6 Bilingual by default
Hệ thống phải được cấu trúc đa ngôn ngữ ngay từ đầu:
- toàn bộ label UI đi qua lớp i18n
- không hardcode text mới trong component nếu có thể tránh
- tiếng Anh và tiếng Việt là locale mặc định
- nếu một câu dịch không tự nhiên, được phép giữ nguyên bản gốc miễn là nhất quán

---

## 4. Visual system

## 4.1 Tone & visual direction
- dark, modern, control-plane style
- tập trung vào độ rõ ràng, không quá “marketing glossy”
- card/panel rõ ràng để phù hợp operator workflow
- nhấn mạnh trạng thái, khả năng và hierarchy thay vì trang trí

## 4.2 Color tokens

### Background
- `bg.canvas`: `#050913`
- `bg.canvas-elevated`: `#060b17`
- `bg.panel`: `rgba(14, 20, 38, 0.86)`
- `bg.panel-alt`: `rgba(9, 14, 29, 0.88)`
- `bg.input`: `rgba(9, 13, 24, 0.90)`
- `bg.subtle`: `rgba(11, 17, 31, 0.85)`

### Text
- `text.primary`: `#f7f8ff`
- `text.secondary`: `rgba(219, 224, 255, 0.78)`
- `text.muted`: `rgba(219, 224, 255, 0.68)`
- `text.disabled`: `rgba(219, 224, 255, 0.42)`

### Border
- `border.subtle`: `rgba(255, 255, 255, 0.08)`
- `border.soft`: `rgba(255, 255, 255, 0.06)`
- `border.focus`: `rgba(135, 94, 255, 0.78)`
- `border.active`: `rgba(141, 103, 255, 0.66)`

### Brand / accent
- `accent.primary.500`: `#6d44ff`
- `accent.primary.400`: `#875eff`
- `accent.primary.soft`: `rgba(105, 65, 255, 0.26)`
- `accent.primary.glow`: `rgba(109, 68, 255, 0.32)`

### Semantic
- `success`: `#4de08d`
- `success.soft`: `rgba(59, 174, 121, 0.14)`
- `warning`: `#f2c66d`
- `warning.soft`: `rgba(242, 198, 109, 0.14)`
- `error`: `#ff9ab0`
- `error.soft`: `rgba(223, 75, 102, 0.16)`
- `info`: `#8ec0ff`
- `info.soft`: `rgba(57, 128, 241, 0.14)`

### Provider category badge
- `cloud.badge`: xanh lam mềm
- `self_hosted.badge`: xanh lá mềm
- `hybrid.badge` nếu có thể thêm ở phase sau: tím-xanh

## 4.3 Gradient usage
Gradient chỉ dùng ở các vùng sau:
- primary button
- active state của card / tab / provider pill
- brand logo
- highlight nhẹ trong panel

Không dùng gradient cho text body hoặc quá nhiều badge.

## 4.4 Typography

### Font family
- primary: `Inter`
- fallback: `ui-sans-serif`, `system-ui`, `Segoe UI`, `sans-serif`

### Font scale
- `display.l`: 32–36px / 700
- `heading.1`: 24–28px / 700
- `heading.2`: 18–20px / 700
- `heading.3`: 15–16px / 600
- `body`: 14–15px / 400–500
- `caption`: 12–13px / 500
- `micro`: 11–12px / 500

### Rules
- page title dùng `heading.1`
- panel title dùng `heading.2`
- eyebrow dùng uppercase + tracking rộng
- table header không quá đậm
- body text ưu tiên dễ đọc, tránh quá nhỏ

## 4.5 Radius
- `radius.sm`: 10px
- `radius.md`: 14px
- `radius.lg`: 18px
- `radius.xl`: 22px
- `radius.2xl`: 24–28px
- `radius.pill`: 999px

## 4.6 Shadow
- panel: `0 14px 44px rgba(0,0,0,0.22)`
- primary button: `0 14px 32px rgba(109,68,255,0.32)`
- active card: `0 0 0 1px rgba(143,105,255,0.18)` + panel shadow nhẹ

## 4.7 Spacing scale
- 4 / 8 / 10 / 12 / 14 / 16 / 18 / 20 / 24 / 28 / 32
- panel padding mặc định: `20px`
- khoảng cách giữa page sections: `18px`
- khoảng cách giữa control inline: `8–12px`

---

## 5. Component style rules

## 5.1 Buttons

### Primary button
Dùng cho hành động chính của một panel.

Style:
- nền gradient tím
- text trắng
- font 700
- bo góc lớn
- có shadow
- full width nếu là CTA chính trong form

Ví dụ:
- `Create project`
- `Queue synthesis job`
- `Use this voice`

### Ghost button
Dùng cho hành động phụ.

Style:
- nền tối nhẹ
- viền subtle
- không đậm bằng primary

Ví dụ:
- `Manage projects`
- `Open notifications`
- `Open full-screen voice picker`

### Icon button
Dùng trong bảng và action row.
- kích thước vuông nhỏ
- icon rõ
- hover state nhẹ

### Tab pill / locale chip
- hình pill
- active state dùng accent soft + active border
- không quá nặng shadow

## 5.2 Inputs
- nền tối đồng nhất
- viền subtle
- focus ring tím
- label luôn đặt phía trên
- placeholder không quá sáng

## 5.3 Cards

### Panel card
Container chính cho từng vùng chức năng.
- nền tối có blur nhẹ
- viền subtle
- radius 24px

### Entity card
Dùng cho project, provider, voice.
- radius 18px
- hover state rõ nhưng không quá chói
- active state có active border + background nâng nhẹ

## 5.4 Badges & chips

### Status badge
- queued/running: info tone
- succeeded/online/active: success tone
- failed/offline/archived: error tone

### Capability chip
- nền neutral soft
- text nhỏ
- không dùng icon mặc định ở phase hiện tại

---

## 6. Information architecture

## 6.1 Navigation cấp 1

### Core
- Dashboard
- Create Job
- Jobs
- Results
- Notifications

### Admin / Configuration
- Projects
- Voice Catalog
- Voice Lab
- Providers
- Settings

## 6.2 Role của từng trang

### Dashboard
Tổng quan realtime.
Mục tiêu: biết hệ thống có ổn không, job nào đang chạy, project nào đáng chú ý.

### Create Job
Trang thao tác thường xuyên nhất.
Mục tiêu: tạo job nhanh nhưng vẫn đủ rõ ràng.

### Jobs
Theo dõi queue và debug.

### Results
Kho audio đầu ra.
Tách riêng khỏi Jobs để tránh phải mở từng job chỉ để lấy file.

### Notifications
Inbox vận hành từ SSE.

### Projects
Nơi quản lý default provider, output format, tags, status.

### Voice Catalog
Trang khám phá và so sánh voice.

### Voice Lab
Trang nghiên cứu / chuẩn bị cho clone voice và custom voice.

### Providers
Trang health + capability matrix.

### Settings
Workspace defaults + system diagnostics.

---

## 7. Core UX flows

## 7.1 Flow A — Tạo job nhanh
1. vào `Create Job`
2. chọn project
3. project tự áp default output / engine nếu có
4. bấm `Open voice picker`
5. chọn engine
6. lọc quốc gia / locale
7. chọn voice
8. nghe sample nếu provider hỗ trợ
9. quay về form
10. nhập script
11. chỉnh advanced settings nếu cần
12. queue job
13. SSE tự cập nhật trạng thái

### Điều bắt buộc
- selected voice summary luôn nhìn thấy được
- nếu chưa chọn voice thì CTA chính phải disabled
- advanced fields phải bám theo provider, không hiện tràn lan

## 7.2 Flow B — Duyệt voice đa engine
1. vào `Voice Catalog`
2. bấm mở voice picker lớn
3. chọn engine ở cột trái
4. xem các locale/quốc gia khả dụng
5. xem danh sách voice có avatar hoặc fallback initials
6. nếu provider có sample thì nghe thử
7. xem capability badges và metadata
8. apply vào selected voice

### Lý do không dùng select đơn giản
Với nhiều engine TTS, dropdown là quá nghèo ngữ cảnh. Người dùng cần:
- so sánh engine
- nhìn locale coverage
- nhận biết voice có sample hay không
- thấy avatar / style / capability trong cùng luồng

## 7.3 Flow C — Quản lý project
1. vào `Projects`
2. xem project cards + stats
3. tạo project mới
4. set default provider/output
5. quay lại `Create Job` dùng project đó

## 7.4 Flow D — Theo dõi job và lỗi
1. vào `Jobs`
2. lọc trạng thái
3. mở chi tiết job
4. xem event timeline
5. nếu lỗi, mở `Notifications`

## 7.5 Flow E — Tìm lại audio kết quả
1. vào `Results`
2. search theo project/provider/script
3. mở hoặc tải artifact

---

## 8. Voice picker design

## 8.1 Tại sao voice picker phải lớn
Vì đây là thành phần quyết định chất lượng UX của sản phẩm.
Nếu voice picker kém, người dùng sẽ không hiểu hệ thống nhiều engine hoạt động thế nào.

## 8.2 Layout đề xuất

### Cột trái — Engine list
- mỗi engine là một card
- hiển thị label + key
- hiển thị capability chips chính
- chọn engine xong mới sang bước locale/voice

### Cột giữa — Locale + voice list
- thanh search
- danh sách locale/quốc gia dưới dạng chip
- danh sách voice theo engine hiện chọn
- mỗi voice card có:
  - avatar hoặc fallback initials
  - display name
  - language + locale
  - provider category
  - capability chips
  - mô tả ngắn

### Cột phải — Selected voice detail
- avatar lớn hơn
- metadata chính
- style/tags
- audio preview nếu có
- CTA `Use this voice`

## 8.3 Behavior rules
- đổi engine thì reset locale filter về `all`
- giữ selected voice nếu vẫn thuộc engine hiện tại
- nếu provider không có preview thì vẫn cho chọn bình thường, nhưng phải hiển thị rõ `Preview unavailable`
- nếu provider có avatar thì dùng ảnh; nếu không thì dùng initials fallback

## 8.4 Preview behavior
- preview audio không autoplay
- chỉ hiển thị player khi provider trả `preview_url`
- nếu không có sample, hiển thị thông báo nhẹ nhàng chứ không xem như lỗi

---

## 9. Multi-language design

## 9.1 Locales hiện tại
- `vi`
- `en`

## 9.2 Nguyên tắc i18n
- label UI đi qua dictionary
- route title đi qua dictionary
- nav label đi qua dictionary
- không hardcode text mới trong component nếu có thể tránh
- backend/provider metadata có thể giữ nguyên ngôn ngữ gốc

## 9.3 Điều được phép không dịch
- provider key
- technical parameter key
- một số thuật ngữ nếu dịch không tự nhiên, ví dụ `Voice Lab`, `style prompt`, `provider`

## 9.4 Nguyên tắc copywriting
- câu ngắn, rõ, thiên thao tác
- không quá marketing
- ưu tiên nhấn mạnh hành động và kết quả

---

## 10. Project UX model

Project cần được xem là lớp “context container”.

Một project nên chứa hoặc dẫn tới:
- mục đích sử dụng
- default engine/provider
- default output format
- tags
- presets (phase sau)
- results / jobs liên quan
- clone voices private cho project (phase sau)

### Những hành động project quan trọng
- create
- use / activate as current context
- archive
- đổi defaults
- xem stats

### Không nên làm
- nhồi toàn bộ settings nâng cao vào project ở giai đoạn đầu
- biến project thành màn hình cài đặt quá nặng

---

## 11. Notifications UX model

Notifications không chỉ là “log”. Nó là inbox vận hành.

Nên ưu tiên các loại event:
- failed
- completed
- started
- warning / provider unavailable (phase sau)

### UX rules
- badge số chưa đọc ở topbar
- vào trang Notifications thì mark seen
- SSE đẩy event mới vào đầu danh sách
- không cần full audit log ở phase này

---

## 12. Results library UX model

Results là một bề mặt riêng.

### Tại sao cần tách khỏi Jobs
- Jobs phục vụ monitoring
- Results phục vụ retrieval / reuse

### Result card cần có
- project
- provider / voice id
- snippet script
- completed time
- duration
- open
- download

Phase sau có thể thêm:
- audio preview inline
- waveform
- favorite
- move/copy to project collection

---

## 13. Clone voice — research direction (ý tưởng trước, chưa implement)

## 13.1 Kết luận chiến lược
Không nên trộn clone voice vào form `Create Job`.
Clone voice là một bounded workflow riêng trong `Voice Lab`.

## 13.2 Recommended stages

### Stage 1 — Draft-only clone workflow
- chọn provider hỗ trợ cloning
- nhập tên voice draft
- chọn ngôn ngữ chính
- upload audio tham chiếu
- điền consent metadata
- chạy validation tự động
- test 3–5 prompt mẫu
- lưu dưới trạng thái `draft`

### Stage 2 — Review & QA
- quality score sơ bộ
- flag nếu audio quá ngắn, quá ồn, có nhạc nền, nhiều speaker
- note người tạo / thời gian tạo
- publish hoặc reject

### Stage 3 — Publish to project catalog
- gán voice vào project hoặc workspace
- set visibility: private / shared / approved only
- cho dùng trong Create Job picker

## 13.3 Consent UX
Clone voice là vùng nhạy cảm.
UI nên bắt buộc có các trường:
- người sở hữu giọng nói
- người upload audio
- xác nhận có quyền sử dụng
- mục đích sử dụng
- trạng thái kiểm tra consent

Không nên cho publish voice clone ngay chỉ bằng upload file xong là xong.

## 13.4 Suggested future entity model
- `voice_drafts`
- `voice_consent_records`
- `voice_reviews`
- `voice_publish_targets`

## 13.5 Vì sao nên đi theo hướng này
- tách biệt job sinh audio thường với job tạo voice
- dễ thêm approval workflow
- giảm rủi ro UX và compliance
- mở đường cho project-scoped custom voices sau này

---

## 14. React architecture rules cho frontend

Frontend nên tiếp tục giữ các nguyên tắc:
- page component chỉ làm orchestration vừa đủ
- stateful logic gom vào hooks
- component hiển thị tách riêng khỏi business logic
- derived state dùng `useMemo`, tránh effect không cần thiết
- filter/search dùng `useDeferredValue` khi hợp lý
- modal/dialog là reusable component, không copy-paste flow chọn voice ở nhiều nơi
- i18n context là nguồn sự thật duy nhất cho locale hiện tại

---

## 15. Danh sách component trọng tâm

### Layout
- `Sidebar`
- `Topbar`
- `Panel`

### Data views
- `JobTable`
- `LiveEventList`
- `StatusBadge`

### Voice system
- `VoiceAvatar`
- `VoiceCard`
- `VoicePickerDialog`

### Future
- `ProjectSelector`
- `ProviderDiagnosticsPanel`
- `ResultAudioCard`
- `NotificationCenter`
- `VoiceCloneWizard`

---

## 16. Checklist khi chỉnh UI về sau

Trước khi merge một thay đổi UI, tự kiểm tra:

1. có làm luồng `project → voice → config → queue → monitor → result` rõ hơn không?
2. có làm voice picker dễ nhìn hơn hay tệ đi?
3. có phá bilingual structure không?
4. có nhét quá nhiều field vào Create Job không?
5. có tách đúng chỗ giữa monitoring và retrieval không?
6. có giữ consistency về màu, typography, spacing và button hierarchy không?

---

## 17. Kết luận

Thiết kế UI của VoiceForge Studio phải được xem như **operator product** chứ không phải form CRUD thông thường.

Điểm khó nhất và quan trọng nhất là:
- quản lý project rõ ngữ cảnh
- chọn voice đa engine dễ nhìn
- theo dõi realtime không cần F5
- chuẩn bị sẵn nền cho clone/custom voice mà không phá UX hiện tại


## Voice catalog sourcing by engine

### VOICEVOX
- Source of truth: running engine HTTP API.
- Primary list source: `GET /speakers` from the engine.
- Practical metadata we surface: speaker/style names, locale bucket, provider traits, and internal preview URL.
- If the running engine version exposes richer speaker metadata, the adapter can enrich avatar/sample fields later without changing the frontend contract.

### Piper
- Source of truth: installed voice models in the runtime data directory.
- Practical list source in this app: runtime `/voices`, derived from installed `.onnx` models.
- This is intentionally install-aware: the picker only shows voices actually available on the host.

### Kokoro
- Source of truth: curated runtime catalog tied to the installed Kokoro voice set.
- Practical list source in this app: runtime `/voices`.
- The UI should treat Kokoro as a compact multilingual catalog with uneven quality across locales.

### VieNeu-TTS
- Source of truth: preset voices from the installed SDK / remote server.
- Practical list source in this app: runtime `/voices` built from `list_preset_voices()`.
- Voice cloning should not pollute the main picker; cloned/draft voices should appear in Voice Lab first.

## Project script rows

### Why project rows exist
A single text box is fine for one-off generation, but self-host production workflows often need:
- row-by-row narration
- selective re-generation of only failed or changed lines
- mixed voices within one project
- final merged output for the whole script

### Recommended model
- `project_script_rows` is the editable script source of truth.
- Each row can either:
  - inherit the project defaults, or
  - override provider / voice / params locally.
- Rows can be enabled/disabled without deleting them.
- Rows can opt into the final merge via `join_to_master`.

### Recommended operator flow
1. Import or paste a multi-line script into a project.
2. Split into ordered rows.
3. Assign a default provider/voice strategy at the project level.
4. Override only the rows that need a different voice.
5. Queue rows in batch.
6. Re-run only failed or edited rows.
7. Merge completed rows into one final artifact.

### Why merge is separate from synthesis
Merging should be an explicit post-step because operators often need to:
- inspect each line first
- replace a few lines only
- leave some lines out of the final cut
- insert silence or transitions later

### Merge controls
The project-level merge UI should eventually expose:
- merge on/off
- output format
- silence between rows (ms)
- include/exclude row toggle
- final download target

---

## 18. Script Line Editor UI - implemented

`Script Editor` is now a first-class screen, not just an API-ready backend concept.

### Primary UX goal
The editor is designed for long narration projects where a creator needs to manage dozens or hundreds of voice lines without regenerating the whole project every time.

### Layout
- Main table: editable line-by-line script source
- Right rail: import script and master merge controls
- Full voice picker modal: reused for row-level and bulk voice assignment

### Core actions
- Import multiline text into ordered rows
- Add row manually
- Edit title and text per row
- Select rows
- Duplicate selected rows
- Delete selected rows
- Reorder rows with up/down controls
- Toggle enabled status
- Toggle whether a row joins the final master artifact
- Assign voice per row
- Bulk assign voice to selected rows; if none selected, apply to enabled rows
- Queue selected rows
- Queue all enabled rows
- Merge completed rows

### Row state shown in UI
Each row surfaces:
- line number
- title
- source text
- provider/voice summary
- output format override or inherited project format
- enabled flag
- join-to-master flag
- synthesis status
- duration
- error message
- row artifact player/download when available

### Why this is better than one big text box
- Failed rows can be retried independently
- Mixed-voice projects are manageable
- Long scripts stay readable
- Users can inspect every generated line before merging
- Final master export becomes a deliberate post-processing step

### Known design debt
- Table editing is functional but not yet virtualized. For projects with hundreds/thousands of rows, add row virtualization.
- Current backend save is replace-all. Add row-level PATCH when preserving row identity/history matters.
- Merge is simple silence-based concat. Later this can expand to transitions, loudness normalization, and chapter markers.

---

## 16. Provider settings and per-voice parameter UX

### Problem
Mỗi TTS engine có bộ tham số khác nhau. Nếu ép tất cả vào một form chung `speed / pitch / volume` thì UI sẽ sai hoặc gây hiểu nhầm:
- ElevenLabs có `stability`, `similarity_boost`, `style`, `speaker_boost`
- Google TTS dùng `speakingRate`, `pitch`, `volumeGainDb`
- Azure dùng SSML prosody như `rate`, `pitch`, `volume`
- VOICEVOX dùng `speedScale`, `pitchScale`, `intonationScale`, `volumeScale`
- Piper có `length_scale`, `noise_scale`, `noise_w`

### Design decision
Voice controls are **schema-driven**. Backend owns a provider parameter schema; frontend renders it dynamically.

```text
provider selected
  -> provider_key
  -> /settings/voice-parameter-schemas
  -> VoiceParameterPanel
  -> row/job params
  -> provider adapter maps params into provider-specific payload
```

### UX locations

#### Create Job
Show only the parameter controls for the currently selected voice engine.

#### Script Editor
Each row has expandable **Voice settings**. A row can inherit the project voice, or override provider/voice/params.

#### Settings
Settings exposes:
- provider credentials / runtime endpoints
- global merge defaults
- current project defaults
- read-only schema list so users can understand which controls exist per engine

### Precedence
For voice generation:
1. row params override
2. job/create form params
3. project defaults
4. provider defaults

For provider credentials:
1. environment variables
2. database settings from Settings page
3. empty / not configured

This lets self-host users keep secrets in `.env`, while still allowing UI-driven setup during local development.

---

## 17. Merge settings UX

`merge_silence_ms` is not a one-off button parameter only. It belongs to multiple scopes:

- Global default: useful for a single-user local install
- Project default: useful when different projects need different pacing
- Merge action override: useful when making a final master artifact

Recommended UI behavior:
- Settings page edits global/project defaults
- Script Editor reads project defaults into merge controls
- User can still change merge controls before pressing merge

Phase later:
- loudness normalization
- crossfade
- chapter markers
- per-row trailing silence
