# Whitelist for vulture (references to symbols used dynamically by Qt or via strings)
# This file exists only to make static-analysis tools aware that these
# symbols are intentionally used at runtime and should not be reported
# as unused.

import dispatcher
import models
import telemetry_bridge
import utils.widget_finder as widget_finder
import widgets
from widgets.charts import TrajectoryCharts
from widgets.gauge import LinearGauge
from widgets.live_feed import LiveFeedWidget
from widgets.status_led import StatusLED

# dispatcher
_ = getattr(dispatcher, "disconnect_all", None)

# models
_ = getattr(models, "TelemetryTableModel", None) and getattr(models.TelemetryTableModel, "headerData", None)

# telemetry bridge
_ = getattr(telemetry_bridge, "_prev_ts", None)

# widget_finder utilities
_ = getattr(widget_finder, "find_tables", None)
_ = getattr(widget_finder, "find_labels", None)
_ = getattr(widget_finder, "summary", None)

# widgets package helpers
_ = getattr(widgets, "get_widget_class", None)
_ = getattr(widgets, "get_widgets_by_category", None)

# widget instance methods / attributes often used by Qt or Designer
_ = getattr(TrajectoryCharts, "setMarkerSize", None)
_ = getattr(LinearGauge, "getValue", None)
_ = getattr(LinearGauge, "getLabel", None)
_ = getattr(LinearGauge, "setMaxValue", None)
_ = getattr(LiveFeedWidget, "sizeHint", None)
_ = getattr(StatusLED, "sizeHint", None)
_ = getattr(StatusLED, "setStatus", None)
_ = getattr(StatusLED, "getState", None)
_ = getattr(StatusLED, "_alignment", None)
_ = getattr(StatusLED, "_status_property", None)
