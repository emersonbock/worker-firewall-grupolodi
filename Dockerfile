# 1. Use uma imagem base oficial do Python. A versão 'slim' é mais leve.
FROM python:3.11-slim

# 2. Defina o diretório de trabalho dentro do container.
# Todos os comandos a seguir serão executados a partir deste diretório.
WORKDIR /app

# 3. Copie o arquivo de dependências primeiro.
# Isso aproveita o cache do Docker: se o requirements.txt não mudar,
# o passo de instalação não será executado novamente em builds futuros.
COPY requirements.txt .

# 4. Instale as dependências listadas no requirements.txt.
# A flag --no-cache-dir mantém a imagem um pouco menor.
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copie todo o resto do código do seu projeto para o diretório de trabalho no container.
COPY . .

# 6. Comando que será executado quando o container iniciar.
# Usamos o modo "exec" (com colchetes) que é a forma recomendada.
CMD ["python", "main.py"]