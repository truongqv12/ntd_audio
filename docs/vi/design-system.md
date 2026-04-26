# Design system

> **Dành cho AI agent:** đọc trước khi thêm UI component. Dùng token sẵn có trong `frontend/src/styles.css`; không tạo scale song song.
>
> **Dành cho người đọc:** ngôn ngữ thị giác, primitive layout, và bộ quy tắc tương tác nhỏ mà mọi page tuân thủ.

## TL;DR

- **Workspace cho operator, không phải site giới thiệu.** Density và rõ ràng hơn polish.
- **Project → engine → voice → config → queue → monitor → result** là user flow chuẩn.
- **Song ngữ EN + VI** mặc định; không gì render mà không qua lớp i18n.
- Token nằm trong `frontend/src/styles.css` ở đầu file. Component dùng qua CSS variable — không lặp hex literal.

## Design principle

1. **Voice-first.** Mỗi màn hình phục vụ vòng lặp ở trên.
2. **Project-first.** Voice, config, job, result không bao giờ xuất hiện ngoài ngữ cảnh project.
3. **Progressive disclosure.** Action thường: 1 click. Tham số nâng cao: nằm sau toggle rõ ràng.
4. **Large-context picking.** Với 8 engine và hàng chục voice, `<select>` đơn không đủ. Voice picker show engine, locale, capability, preview, avatar.
5. **Realtime trust.** SSE chạy mọi state live; user không bao giờ phải refresh.
6. **Bilingual.** Mọi label đi qua `useT()` — không hardcode chuỗi.

## Token

Khai báo ở đầu `styles.css`:

```css
:root {
  /* Color */
  --vf-color-bg-canvas: #050913;
  --vf-color-bg-panel: rgba(14, 20, 38, 0.86);
  --vf-color-text-primary: #f7f8ff;
  --vf-color-text-secondary: rgba(219, 224, 255, 0.78);
  --vf-color-accent: #6d44ff;
  --vf-color-success: #4de08d;
  --vf-color-warning: #f2c66d;
  --vf-color-error: #ff9ab0;
  --vf-color-info: #8ec0ff;

  /* Radius */
  --vf-radius-sm: 4px;
  --vf-radius-md: 8px;
  --vf-radius-lg: 16px;

  /* Spacing (4px base) */
  --vf-space-1: 4px;
  --vf-space-2: 8px;
  --vf-space-3: 12px;
  --vf-space-4: 16px;
  --vf-space-6: 24px;
  --vf-space-8: 32px;
}
```

Luôn tham chiếu variable. Cần giá trị mới? Thêm token trước, rồi consume.

## Hướng thị giác

- Dark, modern, control-plane.
- Card / panel surface có border tinh tế.
- Status truyền tải bằng cả color **và** icon — chỉ color không accessible.
- Không gradient bóng bẩy trên text body / background; gradient chỉ dành cho accent (CTA, highlight row active).

## Quy tắc component

### Button

- Primary: solid accent, mỗi view tối đa một cái.
- Secondary: outlined / background nhẹ.
- Destructive: tinted đỏ, đòi label rõ ràng ("Hủy job", "Xóa project") — không bao giờ chỉ là icon.

### Input

- Luôn có label đi kèm; placeholder không thay label.
- Trạng thái lỗi hiện inline; không chỉ dựa toast.
- Disabled state khác read-only về thị giác.

### Card / panel

- Header (title + action tùy chọn) → body → footer (tùy chọn). Một pattern xuyên page.
- Empty state là một phần của component, không phải sau-cùng. Show action sẽ tạo row đầu tiên.

### Badge và chip

- Status badge theo màu của `JobStatus` (queued/running/succeeded/failed/canceled).
- Provider chip show engine + locale.

## Information architecture

Navigation cấp 1:

| Route | Mục đích |
|---|---|
| `/` (Dashboard) | Rollup project, job gần đây, glance system health. |
| `/jobs` | Bảng job có phân trang; filter theo status, provider, project, free text. |
| `/projects` | CRUD project + cổng vào script editor. |
| `/voices` | Voice catalog browser. |
| `/library` | Artifact đã hoàn thành, có phân trang. |
| `/monitor` | Health provider, log tail. |
| `/settings` | Credential provider, default, schema. |

## Core flow

### A. Tạo job nhanh

```
Dashboard → "New job" → chọn project → chọn engine + voice → nhập text → submit
```

Ba click, một form. Không hiện param nâng cao trừ khi user toggle.

### B. Duyệt voice xuyên engine

```
/voices → filter theo language → preview → "Use this voice" → pre-fill New Job
```

Filter set ở server (Catalog API) nên scale theo số engine.

### C. Quản lý script (multi-row)

```
/projects/<key>/script → import multiline → assign voice per row → enable / disable row
  → "Queue selected" hoặc "Queue enabled" → đợi → "Merge to master"
```

Drag-and-drop sắp xếp lại row. Override voice per row; param editor per row.

### D. Theo dõi job

```
Bất kỳ page → SSE đẩy update → status badge / progress / done
```

Nếu SSE rớt, UI hạ xuống polling — nhưng có banner thông báo rõ.

## i18n

- Catalog: `frontend/src/i18n/en.json` và `frontend/src/i18n/vi.json`.
- Provider/hook: `frontend/src/i18n.tsx`.
- Thêm key trong **cả hai** file cùng PR. CI fail nếu key thiếu một bên.
- Không nest quá hai cấp — giữ key flat (`jobs.create.submit`).

## Cái gì cố tình không trong doc này

- Pixel spec / mockup. Nằm trong file design ngoài repo.
- Branding. Project trong doc tên "ntd_audio"; UI dùng phrasing trung tính cho cả hai ngôn ngữ.
- Component tương lai / aspirational. Chỉ thêm vào đây sau khi ship.
