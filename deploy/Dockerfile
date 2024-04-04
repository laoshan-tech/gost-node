ARG PYTHON_BASE=3.12-slim
FROM python:$PYTHON_BASE AS builder

RUN pip install --upgrade pdm

ENV PDM_CHECK_UPDATE=false

COPY pyproject.toml pdm.lock README.md /gost-node/
COPY src/ /gost-node/src

WORKDIR /gost-node
RUN pdm install --check --prod --no-editable


FROM python:$PYTHON_BASE

COPY --from=builder /gost-node/.venv/ /gost-node/.venv
ENV PATH="/gost-node/.venv/bin:$PATH"

COPY src /gost-node/src
CMD ["python", "src/node.py"]