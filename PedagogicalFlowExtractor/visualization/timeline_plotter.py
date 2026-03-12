"""Concept Timeline Plotter.

Visualizes when concepts appear in the video timeline using Plotly.
Shows the teaching flow — the order in which concepts are introduced.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def create_timeline_figure(timeline_data: list[dict], title: str = "Concept Timeline"):
    """Create a Plotly timeline figure showing concept appearances.

    Args:
        timeline_data: List of dicts with 'time', 'concept', 'importance'.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    import plotly.graph_objects as go

    if not timeline_data:
        logger.warning("No timeline data to plot")
        fig = go.Figure()
        fig.add_annotation(text="No timeline data available", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False)
        return fig

    # Convert time strings to seconds for positioning
    times_sec = []
    labels = []
    importances = []
    time_labels = []

    for entry in timeline_data:
        t = entry.get("time", "0:00")
        parts = t.split(":")
        try:
            sec = int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            sec = 0
        times_sec.append(sec)
        labels.append(entry.get("concept", "").replace("_", " ").title())
        importances.append(entry.get("importance", 0.5))
        time_labels.append(t)

    # Color scale based on importance — teal to blue gradient
    colors = [f"rgba(77, 208, 225, {0.4 + imp * 0.6})" for imp in importances]

    # Marker sizes based on importance
    sizes = [14 + imp * 22 for imp in importances]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=times_sec,
        y=[1] * len(times_sec),  # All on same horizontal line
        mode="markers+text",
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(width=2, color="rgba(77, 208, 225, 0.8)"),
        ),
        text=labels,
        textposition="top center",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Time: %{customdata}<br>"
            "<extra></extra>"
        ),
        customdata=time_labels,
    ))

    # Add connecting line
    fig.add_trace(go.Scatter(
        x=times_sec,
        y=[1] * len(times_sec),
        mode="lines",
        line=dict(color="rgba(148, 163, 184, 0.2)", width=2, dash="dot"),
        showlegend=False,
        hoverinfo="skip",
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#e2e8f0")),
        xaxis=dict(
            title="Video Time (seconds)",
            showgrid=True,
            gridcolor="rgba(148,163,184,0.08)",
            color="#94a3b8",
            title_font=dict(color="#94a3b8"),
        ),
        yaxis=dict(
            visible=False,
            range=[0.5, 1.8],
        ),
        showlegend=False,
        height=300,
        margin=dict(l=20, r=20, t=50, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def create_frequency_chart(concepts: list[dict], title: str = "Concept Frequency"):
    """Create a horizontal bar chart of concept frequencies.

    Args:
        concepts: List of concept dicts with 'name' and 'frequency'.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    import plotly.graph_objects as go

    if not concepts:
        fig = go.Figure()
        fig.add_annotation(text="No concept data", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False)
        return fig

    # Sort by frequency, take top 15
    sorted_concepts = sorted(concepts, key=lambda x: x.get("frequency", 0))
    top = sorted_concepts[-15:]

    names = [c["name"].replace("_", " ").title() for c in top]
    freqs = [c.get("frequency", 0) for c in top]
    scores = [c.get("importance_score", 0) for c in top]

    colors = [f"rgba(77, 208, 225, {0.4 + s * 0.6})" for s in scores]

    fig = go.Figure(go.Bar(
        x=freqs,
        y=names,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(width=1, color="rgba(77,208,225,0.6)"),
        ),
        hovertemplate="<b>%{y}</b><br>Mentions: %{x}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#e2e8f0")),
        xaxis_title="Frequency",
        xaxis=dict(color="#94a3b8", gridcolor="rgba(148,163,184,0.08)", title_font=dict(color="#94a3b8")),
        yaxis=dict(color="#e2e8f0"),
        height=max(300, len(top) * 30),
        margin=dict(l=20, r=20, t=50, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig
