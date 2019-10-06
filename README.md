# Secret Santa

## Install

Build the image from the Dockerfile

```bash
docker build -t secretsanta:latest .
```

Create a new Docker volume 

```bash
docker volume create --name secretsantavolume
```

Start the docker container with

```bash
docker run -v secretsantavolume:/app -p 5000:5000 secretsanta
```

