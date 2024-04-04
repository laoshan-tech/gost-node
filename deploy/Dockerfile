ARG PYTHON_BASE=3.12-slim
FROM python:$PYTHON_BASE AS builder

RUN pip install --upgrade pdm

ENV PDM_CHECK_UPDATE=false

COPY . /src

WORKDIR /src

RUN pdm install --check --prod --no-editable


FROM python:$PYTHON_BASE

COPY --from=builder /src/.venv/ /src/.venv
ENV PATH="/src/.venv/bin:$PATH"

COPY . /src
CMD ["python", "/src/node.py"]