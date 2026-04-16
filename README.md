# mri Assets CDN

CDN de imagens e assets para o ecossistema mri Qbox Brasil.

## 🌐 Endereço
As imagens são servidas via GitHub Pages em:
`https://assets.mriqbox.com.br/`

## 🚀 Estrutura e Operação

O repositório está organizado em diretórios temáticos:
- `assets/`: Items gerais e objetos do jogo.
- `branding/`: Logotipos e identidade visual.
- `clothing/`: Items de vestuário e ícones relacionados.
- `char/`: Assets relacionados a personagens e customização.
- `faces/`: Fotos de rostos/identidade.
- `parents/`: Assets relacionados a herança/genética.
- `props/`: Propriedades e objetos estáticos.
- `ps-housing/`: Assets para o sistema de moradia.

### 🖼️ Estratégia WebP

Para otimizar a performance e reduzir o consumo de banda, todas as imagens são convertidas para **WebP**.
- **Compatibilidade**: Os arquivos originais (PNG, JPG) são mantidos para garantir compatibilidade com sistemas legados.
- **Transparência**: O script detecta automaticamente canais alpha e usa compressão *lossless* para WebP com transparência.
- **Qualidade**: Compressão padrão de 85 para WebP *lossy*.

## 🛠️ Automação (CI/CD)

O repositório utiliza GitHub Actions para manter a integridade e performance do CDN:

1. **Convert Images to WebP**: Disparado em cada push na `main`. Identifica novas imagens PNG/JPG e gera a versão WebP correspondente.
2. **Build and Deploy**: Compila o site do catálogo de assets e gera o `manifest.json`.
3. **Cleanup Originals** (Manual): Workflow para remover arquivos originais de diretórios específicos quando a compatibilidade não for mais necessária (requer que a versão WebP exista).

## 📊 Manifesto e Catálogo

O arquivo `manifest.json` na raiz contém a lista completa de assets. Ele é estruturado para facilitar o consumo por frontends:
- As imagens são agrupadas por nome base.
- Cada entrada possui um array `variants` com os formatos disponíveis (webp, png, jpg).

O catálogo visual pode ser acessado na URL principal do CDN.

## ⚙️ Scripts

- `convert_to_webp.py`: Script Python para conversão em massa.
- `generate_manifest.py`: Gera o mapeamento de arquivos para o catálogo.

## 📦 Armazenamento

Este repositório utiliza **Git LFS** para gerenciar arquivos binários de imagem, mantendo o histórico compactado e facilitando o clone em ambientes de desenvolvimento.
