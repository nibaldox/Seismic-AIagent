import reflex as rx

# Placeholders para formularios/controles reusables

def section(title: str, *children: rx.Component) -> rx.Component:
    return rx.vstack(
        rx.heading(title, size="4"),
        *children,
        spacing="3",
        width="100%",
    )
