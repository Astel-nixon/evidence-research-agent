"""Illustrative sample source text, not live news or real filings.

Each ticker has an 'initial' batch (what a first pass turns up) and a
'deep' batch (additional sources that only surface once the agent asks
for a second pass). This lets a run exercise the agent's own judgment
about whether the first batch was enough, rather than always handing it
everything at once.
"""

SNIPPETS = {
    "AAPL": {
        "initial": [
            "Reuters, 2026-10-30: Apple supplier reports stronger-than-expected "
            "iPhone component orders for the holiday quarter.",
            "Company filing excerpt: Apple raises quarterly dividend by 4%, "
            "cites strong services growth.",
        ],
        "deep": [
            "Earnings call excerpt: CFO flags 'ongoing supply constraints in "
            "high-end display panels' as a risk to Q1 guidance.",
            "Analyst note: services segment now over 25% of revenue, margin "
            "profile improving.",
        ],
    },
    "NVDA": {
        "initial": [
            "Trade press, 2026-10-28: unconfirmed chatter about order timelines "
            "for next-gen AI accelerators, no specifics given.",
        ],
        "deep": [
            "Regulatory filing excerpt: company discloses an export-control "
            "review affecting one product line in certain regions.",
            "Analyst note: datacenter backlog remains the primary bottleneck "
            "per channel checks.",
        ],
    },
    "JPM": {
        "initial": [
            "Press release: JPMorgan expands small-business lending program "
            "in underserved regions.",
            "Trade press commentary on narrowing net interest margins across "
            "large regional banks.",
        ],
        "deep": [
            "Earnings call excerpt: management reiterates expense discipline "
            "target for next fiscal year.",
            "Regulatory filing excerpt: bank increases loan-loss provisions "
            "modestly, cites 'normalizing credit conditions', not deterioration.",
        ],
    },
}
