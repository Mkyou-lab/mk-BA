# ================================================================
#  CHART GENERATION (Candlestick charts as images)
# ================================================================

import io
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_signal_chart(
    candles: List[dict],
    pair: str,
    direction: str,
    entry_price: float,
    output_path: Optional[Path] = None,
) -> Optional[bytes]:
    """
    Generate a candlestick chart PNG showing the signal.
    Returns bytes of the PNG image, or None if matplotlib unavailable.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyArrowPatch
    except ImportError:
        logger.warning("matplotlib not available - skipping chart generation")
        return None

    try:
        # Use last 30 candles
        display_candles = candles[-30:] if len(candles) > 30 else candles
        n = len(display_candles)
        if n < 5:
            return None

        fig, axes = plt.subplots(2, 1, figsize=(12, 8),
                                  gridspec_kw={"height_ratios": [3, 1]})
        fig.patch.set_facecolor("#0a0e17")

        ax = axes[0]
        ax.set_facecolor("#0a0e17")
        ax.tick_params(colors="#94a3b8")
        ax.spines["bottom"].set_color("#1e293b")
        ax.spines["top"].set_color("#1e293b")
        ax.spines["left"].set_color("#1e293b")
        ax.spines["right"].set_color("#1e293b")

        # Draw candles
        for i, c in enumerate(display_candles):
            color = "#22c55e" if c["close"] >= c["open"] else "#ef4444"
            # Body
            body_bottom = min(c["open"], c["close"])
            body_height = abs(c["close"] - c["open"]) or 0.00001
            rect = plt.Rectangle(
                (i - 0.35, body_bottom), 0.70, body_height,
                facecolor=color, edgecolor=color, linewidth=0.5
            )
            ax.add_patch(rect)
            # Wicks
            ax.plot([i, i], [c["low"], c["high"]], color=color, linewidth=0.8)

        # Entry line
        ax.axhline(y=entry_price, color="#f59e0b", linewidth=1.5,
                   linestyle="--", alpha=0.8, label=f"Entry: {entry_price:.5f}")

        # Arrow
        arrow_color = "#22c55e" if direction == "CALL" else "#ef4444"
        arrow_dir = 0.3 if direction == "CALL" else -0.3
        ax.annotate(
            f"{'▲ CALL' if direction == 'CALL' else '▼ PUT'}",
            xy=(n - 1, entry_price),
            xytext=(n - 5, entry_price + arrow_dir * (entry_price * 0.002)),
            fontsize=14, fontweight="bold", color=arrow_color,
            arrowprops=dict(arrowstyle="->", color=arrow_color, lw=2),
        )

        ax.set_title(
            f"{pair} — {'CALL ▲' if direction == 'CALL' else 'PUT ▼'}",
            color="#f1f5f9", fontsize=14, fontweight="bold", pad=10
        )
        ax.legend(facecolor="#111827", labelcolor="#94a3b8",
                  edgecolor="#1e293b", fontsize=9)
        ax.grid(True, alpha=0.15, color="#1e293b")

        # Volume subplot
        ax2 = axes[1]
        ax2.set_facecolor("#0a0e17")
        for i, c in enumerate(display_candles):
            vol_color = "#22c55e" if c["close"] >= c["open"] else "#ef4444"
            ax2.bar(i, c.get("volume", 0), color=vol_color, alpha=0.6, width=0.7)
        ax2.set_ylabel("Volume", color="#94a3b8", fontsize=9)
        ax2.tick_params(colors="#94a3b8")
        ax2.grid(True, alpha=0.10, color="#1e293b")
        for spine in ax2.spines.values():
            spine.set_color("#1e293b")

        plt.tight_layout(pad=1.5)

        if output_path:
            plt.savefig(str(output_path), facecolor=fig.get_facecolor(),
                        dpi=100, bbox_inches="tight")
            plt.close(fig)
            return output_path.read_bytes()
        else:
            buf = io.BytesIO()
            plt.savefig(buf, format="png", facecolor=fig.get_facecolor(),
                        dpi=100, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return buf.read()

    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        return None