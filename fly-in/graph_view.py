"""Graphical visualization for drone simulation using matplotlib.

Renders a live animated graph showing drone positions, zone types,
and movement over time.
"""

from typing import Any, Dict, Optional, cast
from zone import ZoneType
from graph import Graph


# Zone type color map for matplotlib
ZONE_COLORS: Dict[str, str] = {
    ZoneType.NORMAL.value: "#4A90D9",
    ZoneType.RESTRICTED.value: "#E67E22",
    ZoneType.PRIORITY.value: "#27AE60",
    ZoneType.BLOCKED.value: "#7F8C8D",
}

START_COLOR = "#2ECC71"
END_COLOR = "#E74C3C"
DRONE_COLOR = "#F1C40F"
IN_TRANSIT_COLOR = "#F39C12"


class GraphVisualizer:
    """Renders the drone network graph using matplotlib."""

    def __init__(self, graph: Graph) -> None:
        """Initialize the graph visualizer.

        Args:
            graph: The drone network to visualize.
        """
        self.graph: Graph = graph
        self._available: bool = self._check_matplotlib()

    def _check_matplotlib(self) -> bool:
        """Check if matplotlib is available.

        Returns:
            True if matplotlib can be imported.
        """
        try:
            import matplotlib  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def available(self) -> bool:
        """Return whether graphical visualization is available."""
        return self._available

    def render_static(self, output_path: Optional[str] = None) -> None:
        """Render a static view of the network graph.

        Args:
            output_path: If provided, save to this file path.
        """
        if not self._available:
            print("[GraphVisualizer] matplotlib not available. Skipping.")
            return

        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        ax.set_facecolor("#1a1a2e")
        fig.patch.set_facecolor("#1a1a2e")

        # Draw connections
        for conn in self.graph.connections:
            x1, y1 = conn.zone_a.x, conn.zone_a.y
            x2, y2 = conn.zone_b.x, conn.zone_b.y
            ax.plot(
                [x1, x2], [y1, y2],
                color="#555577",
                linewidth=max(1, conn.max_link_capacity),
                alpha=0.6,
                zorder=1,
            )

        # Draw zones
        for zone in self.graph.zones.values():
            if zone.is_start:
                color = START_COLOR
            elif zone.is_end:
                color = END_COLOR
            else:
                color = ZONE_COLORS.get(zone.zone_type.value, "#4A90D9")

            circle = mpatches.Circle(
                (zone.x, zone.y),
                radius=0.3,
                color=color,
                zorder=3,
            )
            ax.add_patch(circle)

            # Zone label
            label = zone.name
            if len(label) > 12:
                label = label[:10] + ".."
            ax.annotate(
                label,
                (zone.x, zone.y - 0.5),
                ha="center",
                va="top",
                fontsize=6,
                color="#cccccc",
                zorder=4,
            )

            # Capacity
            if not zone.is_start and not zone.is_end:
                ax.annotate(
                    str(zone.max_drones),
                    (zone.x, zone.y),
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    fontweight="bold",
                    zorder=5,
                )

        # Legend
        legend_items = [
            mpatches.Patch(color=START_COLOR, label="Start/End"),
            mpatches.Patch(color=ZONE_COLORS[ZoneType.NORMAL.value],
                           label="Normal"),
            mpatches.Patch(
                color=ZONE_COLORS[ZoneType.RESTRICTED.value],
                label="Restricted (2T)"
            ),
            mpatches.Patch(
                color=ZONE_COLORS[ZoneType.PRIORITY.value], label="Priority"
            ),
        ]
        ax.legend(
            handles=legend_items,
            loc="upper right",
            facecolor="#16213e",
            edgecolor="#555577",
            labelcolor="white",
        )

        ax.set_title(
            "Drone Network Graph",
            color="white",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_xlabel("X", color="#aaaaaa")
        ax.set_ylabel("Y", color="#aaaaaa")
        ax.tick_params(colors="#aaaaaa")
        for spine in ax.spines.values():
            spine.set_edgecolor("#555577")

        ax.autoscale()
        ax.margins(0.15)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            print(f"[GraphVisualizer] Graph saved to {output_path}")
        else:
            plt.show()

        plt.close(fig)

    def render_with_drones(
        self,
        drone_positions: Dict[str, int],
        turn: int,
        output_path: Optional[str] = None,
        total_turns: Optional[int] = None,
    ) -> None:
        """Render the network with drone positions overlaid.

        Active zones (containing drones) are highlighted in yellow with the
        drone count shown in a badge. Empty zones are dimmed.

        Args:
            drone_positions: Map of zone_name -> drone count.
            turn: Current simulation turn number.
            output_path: If provided, save to this file path.
            total_turns: Optional total turns count for title display.
        """
        if not self._available:
            return

        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        ax.set_facecolor("#1a1a2e")
        fig.patch.set_facecolor("#1a1a2e")

        # Draw connections
        for conn in self.graph.connections:
            ax.plot(
                [conn.zone_a.x, conn.zone_b.x],
                [conn.zone_a.y, conn.zone_b.y],
                color="#555577",
                linewidth=max(1, conn.max_link_capacity),
                alpha=0.6,
                zorder=1,
            )

        # Draw zones — active zones highlighted, idle zones dimmed
        for zone in self.graph.zones.values():
            drones_here = drone_positions.get(zone.name, 0)
            is_active = drones_here > 0

            if zone.is_start:
                base_color = START_COLOR
            elif zone.is_end:
                base_color = END_COLOR
            else:
                base_color = ZONE_COLORS.get(zone.zone_type.value, "#4A90D9")

            radius = 0.30 if not is_active else 0.40
            alpha = 1.0 if is_active else 0.35

            circle = mpatches.Circle(
                (zone.x, zone.y),
                radius=radius,
                color=base_color,
                alpha=alpha,
                zorder=3 if not is_active else 4,
                ec="#FFFF00" if is_active else "none",
                lw=3 if is_active else 0,
            )
            ax.add_patch(circle)

            # Drone count badge (yellow circle, top-right of zone)
            if drones_here > 0:
                badge = mpatches.Circle(
                    (zone.x + 0.18, zone.y + 0.18),
                    radius=0.13,
                    color="#FFD700",
                    zorder=6,
                    ec="black",
                    lw=1.5,
                )
                ax.add_patch(badge)
                ax.annotate(
                    str(drones_here),
                    (zone.x + 0.18, zone.y + 0.18),
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="black",
                    fontweight="bold",
                    zorder=7,
                )

            # Zone label below
            short = zone.name if len(
                zone.name) <= 12 else zone.name[:10] + ".."
            ax.annotate(
                short,
                (zone.x, zone.y - 0.55),
                ha="center",
                va="top",
                fontsize=6,
                color="#cccccc",
                zorder=4,
            )

        # Title
        title = f"Turn {turn}"
        if total_turns:
            title += f" / {total_turns}"
        title += f" — {sum(drone_positions.values())} drone(s) in motion"

        ax.set_title(title, color="white", fontsize=14, fontweight="bold")

        # Legend
        legend_items = [
            mpatches.Patch(color=START_COLOR, label="Start/End"),
            mpatches.Patch(
                color=ZONE_COLORS[ZoneType.NORMAL.value], label="Normal"
            ),
            mpatches.Patch(
                color=ZONE_COLORS[ZoneType.RESTRICTED.value],
                label="Restricted"
            ),
            mpatches.Patch(
                color=ZONE_COLORS[ZoneType.PRIORITY.value], label="Priority"
            ),
            mpatches.Patch(color="#FFD700", label="Drone count"),
        ]
        ax.legend(
            handles=legend_items,
            loc="upper right",
            facecolor="#16213e",
            edgecolor="#555577",
            labelcolor="white",
            fontsize=8,
        )

        ax.set_xlabel("X", color="#aaaaaa")
        ax.set_ylabel("Y", color="#aaaaaa")
        ax.tick_params(colors="#aaaaaa")
        for spine in ax.spines.values():
            spine.set_edgecolor("#555577")

        ax.autoscale()
        ax.margins(0.15)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=100, bbox_inches="tight")
        else:
            plt.show()

        plt.close(fig)

    def animate(
        self,
        occupancy_log: "list[Dict[str, int]]",
        interval_ms: int = 800,
    ) -> None:
        """Show a live animation of the simulation in a matplotlib window.

        Each frame shows the zone occupancy at one turn. The window stays
        open until the user closes it.

        Args:
            occupancy_log: List of {zone_name: drone_count} per turn.
            interval_ms: Milliseconds between frames.
        """
        if not self._available:
            return
        if not occupancy_log:
            return

        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.animation import FuncAnimation

        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        fig.patch.set_facecolor("#1a1a2e")

        total = len(occupancy_log)

        def draw_frame(frame_idx: int) -> None:
            ax.clear()
            ax.set_facecolor("#1a1a2e")
            occ = occupancy_log[frame_idx]

            # Connections
            for conn in self.graph.connections:
                ax.plot(
                    [conn.zone_a.x, conn.zone_b.x],
                    [conn.zone_a.y, conn.zone_b.y],
                    color="#555577",
                    linewidth=max(1, conn.max_link_capacity),
                    alpha=0.6,
                    zorder=1,
                )

            # Zones
            for zone in self.graph.zones.values():
                drones_here = occ.get(zone.name, 0)
                is_active = drones_here > 0

                if zone.is_start:
                    color = START_COLOR
                elif zone.is_end:
                    color = END_COLOR
                else:
                    color = ZONE_COLORS.get(zone.zone_type.value, "#4A90D9")

                radius = 0.40 if is_active else 0.30
                alpha = 1.0 if is_active else 0.35
                circle = mpatches.Circle(
                    (zone.x, zone.y),
                    radius=radius,
                    color=color,
                    alpha=alpha,
                    zorder=3 if not is_active else 4,
                    ec="#FFFF00" if is_active else "none",
                    lw=3 if is_active else 0,
                )
                ax.add_patch(circle)

                if drones_here > 0:
                    badge = mpatches.Circle(
                        (zone.x + 0.18, zone.y + 0.18),
                        radius=0.13,
                        color="#FFD700",
                        zorder=6,
                        ec="black",
                        lw=1.5,
                    )
                    ax.add_patch(badge)
                    ax.annotate(
                        str(drones_here),
                        (zone.x + 0.18, zone.y + 0.18),
                        ha="center",
                        va="center",
                        fontsize=9,
                        color="black",
                        fontweight="bold",
                        zorder=7,
                    )

                short = (
                    zone.name
                    if len(zone.name) <= 12
                    else zone.name[:10] + ".."
                )
                ax.annotate(
                    short,
                    (zone.x, zone.y - 0.55),
                    ha="center",
                    va="top",
                    fontsize=6,
                    color="#cccccc",
                    zorder=4,
                )

            ax.set_title(
                f"Turn {frame_idx + 1} / {total} — "
                f"{sum(occ.values())} drone(s) in network",
                color="white",
                fontsize=14,
                fontweight="bold",
            )
            ax.tick_params(colors="#aaaaaa")
            for spine in ax.spines.values():
                spine.set_edgecolor("#555577")
            ax.autoscale()
            ax.margins(0.15)

        # Create animation; store on fig so it doesn't get garbage collected.
        # FuncAnimation's stub expects a callback returning Iterable[Artist]
        # for blitting; we don't use blit, so we cast to Any to bypass.
        anim = FuncAnimation(
            fig,
            cast(Any, draw_frame),
            frames=total,
            interval=interval_ms,
            repeat=True,
        )
        # Prevent garbage collection of animation
        setattr(fig, "_anim", anim)

        plt.show()
        plt.close(fig)