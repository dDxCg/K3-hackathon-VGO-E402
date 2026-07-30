# Remove Chat History Overlay and Increase Panel Height

## Goal

Simplify the chatbot menu by removing the dedicated question-history screen shown as “Lịch sử phiên”, while giving the desktop chat panel 1.5 cm more vertical space.

## Scope

### Remove the dedicated history interface

- Remove the “Xem lịch sử câu hỏi” item from the chatbot options menu.
- Remove the `vcHist` history overlay, including its header, empty state, question list, back control, and “Xóa toàn bộ hội thoại” control.
- Remove CSS used only by the history overlay and history highlighting.
- Remove JavaScript used only to open, render, navigate, close, or clear from the history overlay.
- Remove history-overlay handling from the global Escape-key flow and conversation-clear flow.

### Preserve related chatbot capabilities

- Keep the in-memory conversation turns used by the active chat session.
- Keep natural-language recall, including questions such as “Tôi đã hỏi những gì?”.
- Keep “Tải bản ghi (.txt)” in the chatbot menu.
- Keep the existing `vcClear` conversation-clear control in the chatbot options menu.
- Do not change chatbot responses, intent matching, composer behavior, or message rendering.

### Increase panel height

- Change the desktop and tablet chat-panel height from `460px` to `calc(460px + 1.5cm)`.
- Keep panel width at `340px`.
- Keep the panel 16 px from the right and bottom edges.
- Preserve `max-height: calc(100dvh - 32px)` so the panel remains viewport-safe.
- Preserve the existing full-screen chat panel at viewport widths of 480 px or less.

## Implementation boundaries

All functional changes are limited to `ui/prototype.html`. Existing unrelated edits in that file must be preserved. No session-storage behavior, transcript format, or visual styling outside the removed history interface will be changed.

## Validation

- The options menu no longer contains “Xem lịch sử câu hỏi”.
- No `vcHist` elements or history-overlay event listeners remain.
- “Tải bản ghi (.txt)” and the normal clear-conversation control still work.
- Natural-language recall remains present in the intent and response flow.
- The desktop panel uses the exact CSS height `calc(460px + 1.5cm)` (nominally 516.69 px at 96 CSS pixels per inch) while remaining 340 px wide.
- At 480 px and below, the panel remains full-screen.
- JavaScript parses without errors and the edited file passes whitespace validation.
