from pathlib import Path
import re

cpp_path = Path("src/activities/reader/EpubReaderNotesActivity.cpp")
hdr_path = Path("src/activities/reader/EpubReaderNotesActivity.h")
cpp = cpp_path.read_text()
hdr = hdr_path.read_text()

# Notes are a per-book notebook, not bookmarks. Keep old position metadata on
# disk for backward compatibility, but do not display or navigate to it.
pattern = re.compile(
    r"  for \(const auto& note : notes\) \{\n"
    r".*?"
    r"    fui::ListItem item;\n",
    re.S,
)
replacement = """  for (const auto& note : notes) {
    noteSubtitles.emplace_back();

    fui::ListItem item;
"""
cpp, count = pattern.subn(replacement, cpp, count=1)
assert count == 1, "could not replace note list metadata"

pattern = re.compile(
    r"void EpubReaderNotesActivity::openSelectedNote\(\) \{\n"
    r".*?"
    r"\n\}\n\nvoid EpubReaderNotesActivity::activateIndex",
    re.S,
)
replacement = """void EpubReaderNotesActivity::openSelectedNote() {
  if (notes.empty() || nav.selected < 0 || nav.selected >= listCount()) return;
  viewingNote = true;
  requestUpdate(true);
}

void EpubReaderNotesActivity::activateIndex"""
cpp, count = pattern.subn(replacement, cpp, count=1)
assert count == 1, "could not replace openSelectedNote"

needle = """bool EpubReaderNotesActivity::handleButtons() {
"""
insert = """bool EpubReaderNotesActivity::handleButtons() {
  if (viewingNote) {
    if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
      viewingNote = false;
      requestUpdate(true);
      return true;
    }
    if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
      startEdit();
      return true;
    }
    return false;
  }

"""
assert needle in cpp, "handleButtons marker missing"
cpp = cpp.replace(needle, insert, 1)

needle = """  renderer.drawText(UI_12_FONT_ID, titleX, 15 + contentY, tr(STR_NOTES), true, EpdFontFamily::BOLD);

  renderUi();
"""
insert = """  renderer.drawText(UI_12_FONT_ID, titleX, 15 + contentY, tr(STR_NOTES), true, EpdFontFamily::BOLD);

  if (viewingNote && !notes.empty() && nav.selected >= 0 && nav.selected < listCount()) {
    const auto& metrics = UITheme::getInstance().getMetrics();
    const int textX = contentX + metrics.contentSidePadding;
    const int textWidth = contentWidth - 2 * metrics.contentSidePadding;
    const int lineHeight = renderer.getLineHeight(UI_12_FONT_ID);
    int y = contentY + metrics.topPadding + metrics.headerHeight + metrics.verticalSpacing * 2;
    const int hintsTop = renderer.getScreenHeight() - metrics.buttonHintsHeight;
    const int maxLines = std::max(1, (hintsTop - y - metrics.verticalSpacing) / lineHeight);
    const auto lines = renderer.wrappedText(UI_12_FONT_ID, notes[nav.selected].text.c_str(), textWidth, maxLines);
    for (const auto& line : lines) {
      renderer.drawText(UI_12_FONT_ID, textX, y, line.c_str());
      y += lineHeight;
    }

    const auto labels = mappedInput.mapLabels(tr(STR_BACK), tr(STR_EDIT_NOTE), "", "");
    GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
    renderer.displayBuffer();
    return;
  }

  renderUi();
"""
assert needle in cpp, "render marker missing"
cpp = cpp.replace(needle, insert, 1)

needle = "  bool confirmingDelete = false;\n"
replacement = "  bool confirmingDelete = false;\n  bool viewingNote = false;\n"
assert needle in hdr, "header state marker missing"
hdr = hdr.replace(needle, replacement, 1)

cpp_path.write_text(cpp)
hdr_path.write_text(hdr)
