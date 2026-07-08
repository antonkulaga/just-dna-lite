"""Custom draggable div component.

Reflex's newer versions removed drag events (on_drag_start, on_drag_over,
on_drop) from standard HTML elements like Div and ReactRouterLink.
This component re-adds those triggers by subclassing rx.el.Div and
declaring them as EventHandler-typed fields, which is the API that
get_event_triggers() in this Reflex version reads via args_specs_from_fields().
"""

import reflex as rx


def drop_tab_spec(e: rx.Var) -> tuple[rx.Var[str], rx.Var[str]]:
    """Event-arg spec for on_drop: extract (source_id, target_id) client-side.

    The whole gesture is resolved on the drop event — no on_drag_start round-trip
    stashing state on the server (see UploadState.move_tab):

    - target id comes straight off the drop element's own ``data-tab-id``.
    - source id is read from ``data-drag-src`` on the tab-menu container, which
      TAB_DRAG_JS sets during dragstart. We deliberately do NOT read it back from
      the drag's ``dataTransfer``: Firefox doesn't reliably expose dataTransfer
      data through React's synthetic onDrop event (Chromium does), so relying on
      it silently breaks reorder in Firefox. The DOM attribute works everywhere.

    Vars are built off ``e._js_expr`` so they track whatever name Reflex gives
    the event param.
    """
    src = rx.Var(
        _js_expr='(document.querySelector("#right-panel-tab-menu")?.dataset?.dragSrc ?? "")',
        _var_type=str,
    )
    dst = rx.Var(_js_expr=f"{e._js_expr}.currentTarget.dataset.tabId", _var_type=str)
    return (src, dst)


class DraggableDiv(rx.el.Div):
    """A <div> that supports HTML5 drag-and-drop event triggers.

    Actively wired in _tab_item(): on_drag_over, on_drop. on_drop carries
    (source_id, target_id) via drop_tab_spec; dragstart is handled client-side
    in TAB_DRAG_JS. Kept as extension points (not yet wired): on_drag_start,
    on_drag_end, on_drag_enter, on_drag_leave, on_drag.
    """

    on_drag_start: rx.EventHandler     # extension point
    on_drag_end: rx.EventHandler       # extension point
    on_drag_enter: rx.EventHandler     # extension point
    on_drag_leave: rx.EventHandler     # extension point
    on_drag_over: rx.EventHandler
    on_drop: rx.EventHandler[drop_tab_spec]
    on_drag: rx.EventHandler           # extension point


draggable_div = DraggableDiv.create
