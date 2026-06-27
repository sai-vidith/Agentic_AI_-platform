# Node.js alpine base image
FROM node:18-alpine

WORKDIR /app

# Copy package descriptors
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source code
COPY . .

# Expose port 3000
EXPOSE 3000

# Start Vite in development mode
CMD ["npm", "run", "dev"]
