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
RUN tlmgr update --self
RUN tlmgr install sttools preprint siunitx caption footmisc newtxtt tex-gyre newtx oberdiek microtype enumitem biblatex csquotes biber
RUN tlmgr install babel-english; exit 0
RUN tlmgr path add 

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="$PATH:/root/.local/bin/"
RUN uv python install 3.14

# Print simple instructions to the screen 
RUN touch "/root/.bashrc"
RUN echo "echo Using jacow-latex-template from https://github.com/DavidPost-1/jacow-latex-template" >> /root/.bashrc
RUN echo "echo First run \'make\' and verify ./src/main.pdf has compiled" >> /root/.bashrc
RUN echo "echo ''" >> /root/.bashrc
RUN echo "echo Paper layout in ./src/main.tex."
RUN echo "echo Use \\\\\\\\input\{content/\<filename\>.tex\} to define structure." >> /root/.bashrc
RUN echo "echo Section content in ./src/content/\<filename\>.tex."
RUN echo "echo At least one file per section.\n\n" >> /root/.bashrc
RUN echo "echo ''" >> /root/.bashrc
RUN echo "echo Generate submission source with \'make submission\', check ./build directory." >> /root/.bashrc