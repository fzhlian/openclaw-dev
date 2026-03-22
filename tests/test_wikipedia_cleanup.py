from __future__ import annotations

from app.extraction import extract_article
from app.models import ExtractedArticle
from app.analysis import summarize_threads


WIKIPEDIA_HTML = """
<html lang="en">
  <head>
    <title>Dhurandhar: The Revenge - Wikipedia</title>
    <meta property="og:site_name" content="Wikipedia" />
  </head>
  <body>
    <p>Dhurandhar: The Revenge &#91;a&#93; is a 2026 Indian Hindi-language spy action thriller film directed by Aditya Dhar. It is a sequel to the 2025 film Dhurandhar and follows an undercover agent who returns to stop a larger conspiracy.</p>
    <p>The film was released in theatres on 19 March 2026 and received mixed reviews, with praise for scale and criticism for propaganda-heavy messaging.</p>
    <p>The first single titled "Aari Aari" was released on 12 March 2026.</p>
    <p>The official trailer released on 7 March 2026.</p>
  </body>
</html>
"""


def test_wikipedia_extract_article_cleans_title_source_and_citations(tmp_path):
    article = extract_article(
        "https://en.wikipedia.org/wiki/Dhurandhar%3A_The_Revenge?wprov=sfla1",
        raw_html_dir=tmp_path,
        extracted_text_dir=tmp_path,
        fetcher=lambda _: WIKIPEDIA_HTML,
    )

    assert article.title == "Dhurandhar: The Revenge"
    assert article.source == "Wikipedia"
    assert "&#91;" not in article.text
    assert "[a]" not in article.text


def test_wikipedia_summary_prefers_definition_over_music_and_trailer_lines():
    article = ExtractedArticle(
        url="https://en.wikipedia.org/wiki/Dhurandhar%3A_The_Revenge",
        title="Dhurandhar: The Revenge",
        source="Wikipedia",
        author=None,
        published_at=None,
        language="en",
        text=(
            "Dhurandhar: The Revenge is a 2026 Indian Hindi-language spy action thriller film directed by Aditya Dhar. "
            "It is a sequel to the 2025 film Dhurandhar and the final instalment of the duology. "
            "It follows an undercover agent who returns to stop a larger conspiracy. "
            "The film was released in theatres on 19 March 2026 and received mixed reviews, with praise for scale and criticism for propaganda-heavy messaging. "
            "With a runtime of 229 minutes, it is one of the longest Indian films ever produced. "
            "The first single titled Aari Aari was released on 12 March 2026. "
            "The official trailer released on 7 March 2026."
        ),
        word_count=120,
        fetched_at="2026-03-21T00:00:00Z",
    )

    result = summarize_threads(article)

    assert "2026 Indian Hindi-language spy action thriller film" in result["summary"]
    assert "undercover agent" in result["summary"].lower()
    assert "single" not in result["summary"].lower()
    assert "trailer" not in result["summary"].lower()
    assert any("received mixed reviews" in item.lower() for item in result["main_threads"])
    assert all("runtime" not in item.lower() for item in result["main_threads"])
    assert "stars Ranveer" not in result["summary"]
    assert "music composed" not in " ".join(result["main_threads"]).lower()


def test_wikipedia_biography_summary_prefers_lead_paragraph():
    article = ExtractedArticle(
        url="https://en.wikipedia.org/wiki/Arthur_Sullivan",
        title="Arthur Sullivan",
        source="Wikipedia",
        author=None,
        published_at=None,
        language="en",
        text=(
            "Sir Arthur Seymour Sullivan was an English composer. "
            "He is best known for 14 comic opera collaborations with the dramatist W. S. Gilbert. "
            "His works also included orchestral, choral and chamber music. "
            "\n\n"
            "The son of a military bandmaster, Sullivan studied at the Royal Academy of Music and the Leipzig Conservatoire. "
            "His graduation piece The Tempest was received with acclaim in London. "
            "\n\n"
            "In 1866 Sullivan composed Cox and Box. "
            "He later wrote Trial by Jury, H.M.S. Pinafore and The Mikado with Gilbert. "
            "\n\n"
            "Taylor later wrote that there was a peculiar, intangible stamp of Sullivan emerging confidently. "
            "This criticism followed his career."
        ),
        word_count=160,
        fetched_at="2026-03-22T00:00:00Z",
    )

    result = summarize_threads(article)

    assert "English composer" in result["summary"]
    assert "best known for 14 comic operas with Gilbert" in result["summary"]
    assert "intangible stamp" not in result["summary"].lower()
    assert all("intangible stamp" not in item.lower() for item in result["main_threads"])


def test_wikipedia_action_biography_prefers_career_arc_over_credential_list():
    article = ExtractedArticle(
        url="https://en.wikipedia.org/wiki/Chuck_Norris",
        title="Chuck Norris",
        source="Wikipedia",
        author=None,
        published_at=None,
        language="en",
        text=(
            "Carlos Ray Norris was an American martial artist, actor, screenwriter, and author. "
            "He held black belts in karate, taekwondo, Tang Soo Do, Brazilian jiu-jitsu, and judo. "
            "After serving in the United States Air Force, he won martial arts championships. "
            "\n\n"
            "Norris went on to headline a series of commercially successful independent action and martial arts films, "
            "which elevated him to international fame. "
            "In the 1990s, Norris played the title role in the long-running CBS series Walker, Texas Ranger. "
        ),
        word_count=120,
        fetched_at="2026-03-22T00:00:00Z",
    )

    result = summarize_threads(article)

    assert "American martial artist" in result["summary"]
    assert "popular action film star" in result["summary"].lower()
    assert "black belts" not in result["summary"].lower()
