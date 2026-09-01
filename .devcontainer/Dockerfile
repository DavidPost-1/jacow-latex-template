FROM mcr.microsoft.com/devcontainers/base:trixie

# Install perl
RUN apt update
RUN apt install -y perl wget fontconfig

# Install TinyTeX
RUN wget -qO- "https://tinytex.yihui.org/install-bin-unix.sh" | sh

# Put TinyTeX on the path
ENV PATH="$PATH:/root/bin/"
ENV PATH="$PATH:/root/.local/bin"

# Install required tex packages
RUN tlmgr install sttools preprint siunitx caption footmisc newtxtt tex-gyre newtx oberdiek microtype enumitem biblatex csquotes biber
RUN tlmgr install babel-english; exit 0
RUN tlmgr path add 

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
RUN uv python install 3.14