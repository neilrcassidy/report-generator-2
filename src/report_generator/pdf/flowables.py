"""Custom ReportLab flowables. They only draw: values arrive already rounded and
colours already chosen by tier, so nothing here decides a result."""

from reportlab.graphics.shapes import Drawing, Wedge
from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.platypus import Flowable


def _clamp_percent(value: int) -> int:
    return max(0, min(100, value))


class SectionHeader(Flowable):
    """White bold text centred on a rounded, filled bar."""

    def __init__(self, text: str, fill: Color, width: float = 200, height: float = 30) -> None:
        super().__init__()
        self.text = text
        self.fill = fill
        self.width = width
        self.height = height

    def draw(self) -> None:
        canv = self.canv
        canv.setFillColor(self.fill)
        canv.roundRect(0, 0, self.width, self.height, 10, fill=1, stroke=0)
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 12)
        canv.drawCentredString(self.width / 2, self.height / 2 - 4, self.text)


class ProgressBar(Flowable):
    """Rounded horizontal bar with the percentage printed to its right."""

    def __init__(
        self,
        value: int,
        bar_color: Color,
        background: Color,
        width: float = 200,
        height: float = 15,
    ) -> None:
        super().__init__()
        self.value = _clamp_percent(value)
        self.bar_color = bar_color
        self.background = background
        self.width = width
        self.height = height

    def draw(self) -> None:
        canv = self.canv
        radius = self.height / 2
        canv.saveState()
        canv.setFillColor(self.background)
        canv.roundRect(0, 0, self.width, self.height, radius, fill=1, stroke=0)
        fill_width = self.value / 100 * self.width
        if fill_width > 0:
            canv.setFillColor(self.bar_color)
            canv.roundRect(
                0, 0, fill_width, self.height, min(radius, fill_width / 2), fill=1, stroke=0
            )
        canv.setFillColor(colors.black)
        canv.setFont("Helvetica", 10)
        canv.drawString(self.width + 8, self.height / 2 - 3, f"{self.value} %")
        canv.restoreState()


class SemiCircleGauge(Flowable):
    """Half-ring gauge filling left to right, with the percentage in the middle."""

    def __init__(
        self,
        value: int,
        gauge_color: Color,
        background: Color,
        width: float = 180,
        height: float = 120,
        radius: float = 70,
        arc_thickness: float = 14,
    ) -> None:
        super().__init__()
        self.value = _clamp_percent(value)
        self.gauge_color = gauge_color
        self.background = background
        self.width = width
        self.height = height
        self.radius = radius
        self.arc_thickness = arc_thickness
        self.inner_radius = max(1, radius - arc_thickness + 3)

    def draw(self) -> None:
        cx, cy = self.width / 2, self.arc_thickness + 10
        d = Drawing(self.width, self.height)
        d.add(Wedge(cx, cy, self.radius, 0, 180, fillColor=self.background, strokeColor=None))
        sweep = 180 * self.value / 100
        if sweep > 0:
            d.add(
                Wedge(cx, cy, self.radius, 0, sweep, fillColor=self.gauge_color, strokeColor=None)
            )
        d.add(Wedge(cx, cy, self.inner_radius, 0, 180, fillColor=colors.white, strokeColor=None))

        canv = self.canv
        # Wedges sweep counter-clockwise from the right; mirror so the gauge fills from the left.
        canv.saveState()
        canv.translate(self.width, 0)
        canv.scale(-1, 1)
        d.drawOn(canv, 0, 0)
        canv.restoreState()

        canv.setFont("Helvetica-Bold", 28)
        canv.setFillColor(colors.black)
        canv.drawCentredString(self.width / 2, cy + 5, f"{self.value} %")
