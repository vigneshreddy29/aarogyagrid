"""
Visual layer for AarogyaGrid.

Direction
---------
An operations console, not a report. The subject is a supply chain in
active failure — 24 facility-medicine pairs already at zero, 52 more
counting down. The interface should feel like something monitored, so:
deep layered surfaces, status colour carrying real meaning, numerals set
large in monospace because they are the content.

Type: Space Grotesk for display — technical, slightly mechanical, not a
default UI sans. IBM Plex Mono for every figure. IBM Plex Sans for body,
with its Telugu cut for the pharmacist briefings.

Signature: the status ribbon — a full-width band across the head of the
console reporting the single worst facility in the network, always
visible before anything is clicked.
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Telugu:wght@400;500&display=swap');

:root {
  --void:     #0A0E1A;
  --surface:  #131A2A;
  --raised:   #1A2336;
  --line:     #263149;
  --line-lit: #34426240;
  --text:     #E8ECF5;
  --muted:    #8894B0;
  --dim:      #5C6884;

  --critical: #F43F5E;
  --warning:  #FBBF24;
  --steady:   #34D399;
  --accent:   #5B8DEF;
}

.stApp {
  background:
    radial-gradient(1100px 500px at 15% -8%, #16203A 0%, transparent 60%),
    radial-gradient(900px 450px at 88% -5%, #1A1730 0%, transparent 55%),
    var(--void);
}

html, body, [class*="css"] {
  font-family: 'IBM Plex Sans', -apple-system, sans-serif;
  color: var(--text);
}

.block-container {
  padding-top: 2rem;
  padding-bottom: 4rem;
  max-width: 1440px;
}

/* ------------------------------------------------------- masthead */
h1 {
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 700 !important;
  font-size: 2.6rem !important;
  letter-spacing: -0.035em !important;
  line-height: 1.05 !important;
  background: linear-gradient(102deg, #FFFFFF 12%, #8FB4FF 92%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: .2rem !important;
}

h2, h3 {
  font-family: 'Space Grotesk', sans-serif !important;
  letter-spacing: -0.02em !important;
  color: var(--text) !important;
}
h2 { font-size: 1.45rem !important; font-weight: 600 !important; }
h3 { font-size: 1.12rem !important; font-weight: 600 !important; }
h4 {
  font-size: .72rem !important; font-weight: 600 !important;
  letter-spacing: .12em !important; text-transform: uppercase !important;
  color: var(--dim) !important;
}

/* --------------------------------------------- KPI console tiles */
div[data-testid="stMetric"] {
  position: relative;
  overflow: hidden;
  background: linear-gradient(158deg, var(--raised) 0%, var(--surface) 100%);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 16px 18px 14px 20px;
  transition: transform .2s cubic-bezier(.2,.8,.3,1), border-color .2s ease;
}
div[data-testid="stMetric"]::before {
  content: '';
  position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: linear-gradient(180deg, var(--accent), transparent 85%);
}
div[data-testid="stMetric"]:hover {
  transform: translateY(-3px);
  border-color: #3A4A6E;
}
div[data-testid="stMetricLabel"] p {
  font-size: .67rem !important; font-weight: 600 !important;
  letter-spacing: .13em !important; text-transform: uppercase !important;
  color: var(--dim) !important;
}
div[data-testid="stMetricValue"] {
  font-family: 'IBM Plex Mono', monospace !important;
  font-weight: 500 !important;
  font-size: 2.4rem !important;
  letter-spacing: -.04em !important;
  color: #FFFFFF !important;
  line-height: 1.15 !important;
}

/* ------------------------------------------------------- tab rail */
div[data-baseweb="tab-list"] {
  gap: 4px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 5px;
}
button[data-baseweb="tab"] {
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: .82rem !important; font-weight: 500 !important;
  letter-spacing: -.005em;
  color: var(--muted) !important;
  border-radius: 7px !important;
  padding: 8px 15px !important;
  transition: background .16s ease, color .16s ease;
}
button[data-baseweb="tab"]:hover { color: var(--text) !important; background: #1E2942 !important; }
button[data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(160deg, #2A3B60, #1E2942) !important;
  color: #FFFFFF !important; font-weight: 600 !important;
  box-shadow: inset 0 1px 0 #4B62924D;
}
div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] { display: none !important; }

/* ------------------------------------------------------- callouts */
div[data-testid="stAlert"] {
  border-radius: 9px;
  border: 1px solid var(--line);
  border-left-width: 3px;
  background: var(--surface) !important;
  font-size: .89rem;
  padding: 13px 16px;
}

/* ------------------------------------------------------ surfaces */
div[data-testid="stExpander"] {
  background: var(--surface);
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
}
div[data-testid="stExpander"] summary {
  font-size: .87rem; font-weight: 500; color: var(--text);
}
div[data-testid="stExpander"] summary:hover { color: var(--accent); }

div[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface);
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  transition: border-color .18s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color: #3A4A6E !important; }

/* ------------------------------------------ figures and tables */
.js-plotly-plot {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px;
}
div[data-testid="stDataFrame"] {
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  font-variant-numeric: tabular-nums;
}
div[data-testid="stDataFrame"] * { font-size: .81rem !important; }

/* ------------------------------------------------------- controls */
div[data-testid="stTextInput"] input {
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  border-radius: 9px !important;
  font-size: .92rem !important;
  padding: 11px 14px !important;
}
div[data-testid="stTextInput"] input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px #5B8DEF26 !important;
}
div[data-testid="stTextInput"] input::placeholder { color: var(--dim) !important; }

div[data-baseweb="select"] > div {
  background: var(--surface) !important;
  border-color: var(--line) !important;
  border-radius: 9px !important;
}

div[data-testid="stCaptionContainer"] p {
  font-size: .82rem !important; color: var(--muted) !important; line-height: 1.6;
}

hr { border-color: var(--line) !important; margin: 1.5rem 0 !important; }

code {
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: .81rem !important;
  background: #0E1524 !important;
  border: 1px solid var(--line);
  border-radius: 5px;
  color: #93B4FF !important;
}

.telugu, .telugu * {
  font-family: 'IBM Plex Sans Telugu', 'IBM Plex Sans', sans-serif !important;
  line-height: 1.85 !important;
}

/* --------------------------------------------------- entry motion */
.block-container > div { animation: lift .42s cubic-bezier(.2,.8,.3,1) both; }
.block-container > div:nth-child(2) { animation-delay: .04s; }
.block-container > div:nth-child(3) { animation-delay: .08s; }
@keyframes lift {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: none; }
}

@media (prefers-reduced-motion: reduce) {
  .block-container > div { animation: none; }
  div[data-testid="stMetric"] { transition: none; }
}

::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-track { background: var(--void); }
::-webkit-scrollbar-thumb { background: #2A3654; border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: #3A4A6E; }

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
d/* ------------------------------------------ tab rail, forced */
div[data-testid="stTabs"] [role="tablist"] {
  display: flex !important;
  gap: 6px !important;
  background: #131A2A !important;
  border: 1px solid #263149 !important;
  border-radius: 12px !important;
  padding: 6px !important;
  overflow-x: auto !important;
}

div[data-testid="stTabs"] [role="tab"] {
  flex: 0 0 auto !important;
  background: #0E1524 !important;
  border: 1px solid #263149 !important;
  border-radius: 8px !important;
  padding: 9px 16px !important;
  margin: 0 !important;
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: .8rem !important;
  font-weight: 500 !important;
  color: #8894B0 !important;
  white-space: nowrap !important;
  transition: all .16s ease !important;
}

div[data-testid="stTabs"] [role="tab"] p {
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: .8rem !important;
  margin: 0 !important;
}

div[data-testid="stTabs"] [role="tab"]:hover {
  background: #1E2942 !important;
  border-color: #3A4A6E !important;
  color: #E8ECF5 !important;
}

div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: linear-gradient(160deg, #3B5488, #24304C) !important;
  border-color: #5B8DEF !important;
  color: #FFFFFF !important;
  font-weight: 600 !important;
  box-shadow: 0 0 0 1px #5B8DEF33, inset 0 1px 0 #6B84B84D !important;
}

div[data-testid="stTabs"] [role="tab"][aria-selected="true"] p {
  color: #FFFFFF !important;
  font-weight: 600 !important;
}

div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
div[data-testid="stTabs"] [data-baseweb="tab-border"] {
  display: none !important;
  height: 0 !important;
}
</style>
"""

BAND_COLOR = {"HIGH RISK": "#F43F5E", "AT RISK": "#FBBF24",
              "STABLE": "#A3E635", "RESILIENT": "#34D399"}


def apply(st):
    """Inject the style layer. Call once, right after set_page_config."""
    st.markdown(CSS, unsafe_allow_html=True)


def ribbon(st, worst_name, score, band, risk, days, district):
    """Status ribbon — the single worst facility in the network, always visible."""
    c = BAND_COLOR.get(band, "#F43F5E")
    when = "already at zero" if days == 0 else f"{days:.1f} days to stock-out"
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:20px;
              background:linear-gradient(96deg,{c}1F 0%,#131A2A 55%);
              border:1px solid {c}59;border-left:4px solid {c};
              border-radius:12px;padding:15px 26px;margin:6px 0 20px 0">
          <div style="display:flex;align-items:center;gap:9px;flex-shrink:0">
            <span style="width:9px;height:9px;border-radius:50%;background:{c};
                  box-shadow:0 0 0 4px {c}2E;display:inline-block"></span>
            <span style="font-family:'Space Grotesk',sans-serif;font-size:.68rem;
                  font-weight:600;letter-spacing:.15em;color:{c}">HIGHEST RISK</span>
          </div>
          <div style="flex:1;min-width:0">
            <div style="font-family:'Space Grotesk',sans-serif;font-size:1.02rem;
                 font-weight:600;color:#FFF">{worst_name}
              <span style="color:#5C6884;font-weight:400;font-size:.85rem"> · {district}</span>
            </div>
            <div style="font-size:.83rem;color:#8894B0;margin-top:3px">
              {risk} — {when}</div>
          </div>
          <div style="text-align:right;flex-shrink:0">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:2rem;
                 font-weight:500;line-height:1;color:{c}">{score}</div>
            <div style="font-size:.62rem;letter-spacing:.13em;color:#5C6884;
                 margin-top:3px">RESILIENCE</div>
          </div>
        </div>""",
        unsafe_allow_html=True)


def score_card(st, score, band):
    """Large resilience score, set as a console readout."""
    c = BAND_COLOR.get(band, "#F43F5E")
    st.markdown(
        f"""<div style="text-align:center;padding:26px 18px;border-radius:12px;
              background:linear-gradient(158deg,{c}1A,#131A2A);
              border:1px solid {c}4D;border-left:4px solid {c}">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:3.6rem;
               font-weight:500;line-height:1;color:{c}">{score}</div>
          <div style="font-size:.64rem;letter-spacing:.14em;color:#5C6884;
               margin-top:8px">OUT OF 100</div>
          <div style="font-family:'Space Grotesk',sans-serif;font-size:.95rem;
               font-weight:600;margin-top:12px;letter-spacing:.05em;
               color:{c}">{band}</div>
        </div>""",
        unsafe_allow_html=True)


def telugu(st, text):
    """Telugu briefing in its proper cut."""
    st.markdown(
        f"""<div class="telugu" style="background:#34D3990F;
              border:1px solid #34D3994D;border-left:3px solid #34D399;
              border-radius:9px;padding:15px 17px;font-size:.94rem;
              color:#E8ECF5">{text}</div>""",
        unsafe_allow_html=True)


def dark(fig, height=None):
    """Apply the console theme to a plotly figure."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color="#8894B0", size=12),
        xaxis=dict(gridcolor="#1F2A40", zerolinecolor="#263149",
                   linecolor="#263149", tickfont=dict(color="#8894B0")),
        yaxis=dict(gridcolor="#1F2A40", zerolinecolor="#263149",
                   linecolor="#263149", tickfont=dict(color="#8894B0")),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8894B0", size=11)),
        hoverlabel=dict(bgcolor="#1A2336", bordercolor="#34426A",
                        font=dict(family="IBM Plex Sans", color="#E8ECF5", size=12)),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    if height:
        fig.update_layout(height=height)
    return fig