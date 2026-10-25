FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY src ./src
COPY public ./public
# last, so a new commit does not invalidate the dependency layer
# the commit the image was built from, set by the image pipeline
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=$GIT_COMMIT
USER node
EXPOSE 8080
CMD ["node", "src/index.js"]
