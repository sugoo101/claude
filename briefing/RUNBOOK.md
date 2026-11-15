# Emerging Tech Daily: runbook

A scheduled task runs this at **10:00 IST every day**. It produces a 2-3 page PDF
briefing on emerging technology from Hacker News and Y Combinator.

## Steps

1. **Fetch the data**
   `python3 briefing/fetch_sources.py $SCRATCH/sources.json`
   This collects HN top stories (24h, 40+ points, with the top comments on the
   leading 12), Show HN (48h), Launch HN (7d), and YC Launches (last 4 days)
   with tag counts.

2. **Analyse** `sources.json` as a technology analyst. Look for *emerging
   technology*, not general news:
   - Cluster the YC launches and HN stories into 5-6 themes. Name what is new,
     why it matters, and the concrete evidence (votes, points, company names).
   - Rate each theme's momentum: Accelerating / Emerging / Watch / Cooling.
   - Use HN comments to gauge sentiment, including skepticism.
   - Skip off-topic items (politics, retro computing, games) unless they say
     something about where technology is heading.
   - Only state facts that appear in the data. Do not invent numbers.

3. **Write** `$SCRATCH/briefing.json` following the schema in the
   `build_pdf.py` docstring: headline, summary, 4 key_numbers, 5-6 signals,
   6-8 yc_watch rows, 6-8 hn_pulse rows, 4-5 watch_next bullets, sources_note.
   Use plain text in every field (no markdown), and date it in IST.

4. **Render**
   `bash briefing/render.sh $SCRATCH/briefing.json $SCRATCH/emerging-tech-YYYY-MM-DD.pdf`
   (`render.sh` finds a Python that has reportlab, or installs reportlab.)
   Exit code 2 means the PDF is not 2-3 pages. Trim or expand the content and
   re-run until it passes.

5. **Deliver.** Send the PDF to the user with SendUserFile (status
   `proactive`, display `render`), with a 2-3 line caption giving the headline
   and the top three signals.

If a source is unreachable, build the briefing from whatever was fetched and
say so in `sources_note`.
