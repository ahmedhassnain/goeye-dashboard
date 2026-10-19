# Entry point for the Hugging Face Gradio Space.
# The Space runs `python app.py` and serves whatever listens on port 7860, so
# this serves the FastAPI app from api/main.py with a small Gradio status page
# mounted at /ui. Locally, keep using `uvicorn api.main:app`.
import gradio as gr
import uvicorn
from fastapi.responses import RedirectResponse

from api.main import app

with gr.Blocks(title="GoEye API") as status_page:
    gr.Markdown(
        "# GoEye API\n"
        "Backend for the [GoEye dashboard](https://goeye-dashboard.vercel.app). "
        "Interactive API docs are at [/docs](/docs)."
    )


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui")


app = gr.mount_gradio_app(app, status_page, path="/ui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
