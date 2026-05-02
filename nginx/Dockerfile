FROM nginx:alpine

# Install openssl to generate self-signed TLS certificate
RUN apk add --no-cache openssl

# Generate a 10-year self-signed certificate for home network use.
# For production with a real domain, replace this with Let's Encrypt via certbot.
RUN mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 3650 \
        -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/docmind.key \
        -out  /etc/nginx/ssl/docmind.crt \
        -subj "/C=US/ST=Local/L=HomeNetwork/O=DocMind/OU=Self-Signed/CN=docmind.local" \
        -addext "subjectAltName=DNS:docmind.local,DNS:localhost,IP:127.0.0.1"

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
