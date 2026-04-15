import resend

from app.config import RESEND_API_KEY, RESEND_FROM_EMAIL


def send_email(to: str, subject: str, html: str):
    if not RESEND_API_KEY:
        print(f"[mail] RESEND_API_KEY not set — would send to {to}: {subject}")
        return None

    resend.api_key = RESEND_API_KEY
    return resend.Emails.send({
        "from": RESEND_FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
    })


def send_job_alert(to: str, new_matches: list[dict]):
    """Send an email alert with new high-scoring job matches."""
    if not new_matches:
        return

    rows = ""
    for m in new_matches[:10]:
        score_color = "#3cfca2" if m["score"] >= 70 else "#f0b429" if m["score"] >= 40 else "#ff5c5c"
        rows += f"""
        <tr>
            <td style="padding:10px 12px; border-bottom:1px solid #21293a;">
                <strong style="color:#e6edf3;">{m["title"]}</strong><br>
                <span style="color:#6e7681; font-size:13px;">{m["organization"]} &middot; {m["location"]}</span>
            </td>
            <td style="padding:10px 12px; border-bottom:1px solid #21293a; text-align:right;">
                <span style="background:{score_color}22; color:{score_color}; padding:2px 10px; border-radius:12px; font-size:13px; font-weight:600;">{m["score"]:.1f}</span>
            </td>
            <td style="padding:10px 12px; border-bottom:1px solid #21293a; text-align:right;">
                <a href="{m["url"]}" style="color:#00e5ff; text-decoration:none; font-size:13px;">Apply &rarr;</a>
            </td>
        </tr>"""

    html = f"""
    <div style="background:#0d1117; padding:32px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="max-width:600px; margin:0 auto;">
            <h1 style="color:#00e5ff; font-size:20px; margin-bottom:4px;">CyberRank</h1>
            <p style="color:#6e7681; font-size:14px; margin-bottom:24px;">New job matches found</p>

            <div style="background:#151b26; border:1px solid #21293a; border-radius:8px; overflow:hidden;">
                <table style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="background:#1a2233;">
                            <th style="padding:10px 12px; text-align:left; color:#6e7681; font-size:12px; text-transform:uppercase; letter-spacing:0.05em;">Position</th>
                            <th style="padding:10px 12px; text-align:right; color:#6e7681; font-size:12px; text-transform:uppercase; letter-spacing:0.05em;">Score</th>
                            <th style="padding:10px 12px; text-align:right; color:#6e7681; font-size:12px; text-transform:uppercase; letter-spacing:0.05em;">Link</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>

            <p style="color:#6e7681; font-size:13px; margin-top:20px; text-align:center;">
                {len(new_matches)} new match{"es" if len(new_matches) != 1 else ""} above your alert threshold.
            </p>
        </div>
    </div>
    """

    send_email(
        to=to,
        subject=f"CyberRank: {len(new_matches)} new job match{'es' if len(new_matches) != 1 else ''}",
        html=html,
    )
