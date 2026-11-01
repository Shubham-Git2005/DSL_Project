"""Launch SkillsBridge using an already running LM Studio model on loopback."""
import os

import uvicorn


if __name__ == "__main__":
    os.environ["ASSESSOR_PROVIDER"] = "lmstudio"
    os.environ.setdefault("ASSESSOR_MODEL", "qwen2.5-7b-instruct")
    os.environ.setdefault("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    uvicorn.run("prototype.app:app", host="127.0.0.1", port=8001, workers=1)
