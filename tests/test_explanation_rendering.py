from components import cards


def test_escape_html_for_explanation_text():
    raw_text = "<div class='wg-sub'>AI explanation</div>"
    escaped = cards.escape_html(raw_text)
    assert escaped == "&lt;div class=&#x27;wg-sub&#x27;&gt;AI explanation&lt;/div&gt;"
