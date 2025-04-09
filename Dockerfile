
FROM alpine:3.21.2 as build

workdir /app

COPY ./ /app
RUN mkdir -p /tmp/downloads
RUN mkdir -p /app/staging_dir/in
RUN mkdir -p /app/staging_dir/out


RUN apk update 
RUN apk update && apk add --no-cache curl bash strace
RUN apk update  && apk add --no-cache libreoffice bash icu-data-full ttf-dejavu fontconfig
RUN apk add --no-cache openjdk8-jre st thunar tint2
RUN apk add --no-cache py3-pip


RUN /usr/bin/libreoffice --help
RUN find /usr/lib/libreoffice/program -name '*filter*'


RUN apk add --no-cache \
        bash curl tzdata \
        icu icu-libs \
        libstdc++ dbus-x11

RUN apk add --no-cache \
        font-noto-all font-noto-cjk ttf-font-awesome ttf-hack \
        terminus-font \
        ttf-dejavu \
        ttf-freefont \
        ttf-inconsolata \
        ttf-liberation \
        ttf-opensans   \
        fontconfig \
        msttcorefonts-installer

# RUN touch test.pptx
RUN /usr/bin/libreoffice --headless --convert-to pdf:writer_pdf_Export ./test.pptx
RUN /usr/bin/libreoffice --headless --convert-to pdf:impress_pdf_Export ./test.pptx
# RUN cat ./test.pdf
# RUN update-ms-fonts
# RUN fc-cache -fv

# RUN echo "**** openbox tweaks ****" && \
#     sed -i \
#     's/NLMC/NLIMC/g' \
#     /etc/xdg/openbox/rc.xml && \
#     sed -i \
#     '/Icon=/c Icon=xterm-color_48x48' \
#     /usr/share/applications/st.desktop && \
#     echo "**** cleanup ****" && \
#     rm -rf \
#     /tmp/*

RUN fc-cache -f -v
ENV PIP_CONFIG_FILE=/home/nonroot/.pip/pip.conf
# ENV no_proxy=127.0.0.1,localhost
RUN echo "Home is set to: $HOME"
# ENV HOME=/tmp
# RUN echo "Home is changed to: $HOME"
RUN ls -l /tmp
RUN --mount=type=secret,id=artifactory_pipconf,target=/home/nonroot/.pip/pip.conf,uid=10000 \
    python -m pip config -v debug && \
    python -m pip install --upgrade pip --break-system-packages && \
    python -m pip install -r requirements.txt --break-system-packages && \
    which uvicorn

EXPOSE  5000/tcp

RUN chmod +x ./src/run.sh
CMD ["./src/run.sh"]
