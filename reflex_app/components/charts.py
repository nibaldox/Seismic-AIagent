import reflex as rx

# Placeholders para wrappers de charts (Plotly/otros)

def placeholder_chart(title: str) -> rx.Component:
    return rx.box(
        rx.heading(title, size="4"),
        rx.box("Chart placeholder", border="1px dashed #444", padding="24px", border_radius="8px"),
        width="100%",
    )
