import reflex as rx

NAV_ITEMS = [
    ("Inicio", "/"),
    ("Waveform", "/waveform"),
    ("Spectrum", "/spectrum"),
    ("Histogramas", "/histograms"),
    ("AI Interpreter", "/ai_interpreter"),
    ("Location 1D", "/location_1d"),
]


def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(rx.text("🌊", font_size="1.5rem"), rx.heading("Seismic AIagent", size="5")),
            *[rx.link(text, href=href) for text, href in NAV_ITEMS],
            spacing="3",
        ),
        width="260px",
        padding="16px",
        border_right="1px solid #2b2b2b",
        bg="#111",
    )


def app_shell(content: rx.Component) -> rx.Component:
    return rx.box(
        rx.hstack(
            sidebar(),
            rx.box(content, flex="1", padding="20px"),
        ),
        min_h="100vh",
        bg="#0a0a0a",
        color="#e6e6e6",
    )
