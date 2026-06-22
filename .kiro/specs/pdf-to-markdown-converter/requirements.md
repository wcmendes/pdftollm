# Requirements Document

## Introduction

Sistema desktop multiplataforma (Linux e Windows) para conversão de arquivos PDF em Markdown. O usuário pode selecionar múltiplos arquivos PDF de uma pasta, escolher uma pasta de destino e exportar os arquivos convertidos mantendo o mesmo nome do arquivo original. O sistema oferece a opção de extrair imagens e objetos embutidos nos PDFs para uma subpasta associada.

## Glossary

- **Aplicação**: O aplicativo desktop de conversão de PDF para Markdown
- **Usuário**: A pessoa que opera a Aplicação
- **Arquivo_Fonte**: Um arquivo PDF selecionado pelo Usuário para conversão
- **Arquivo_Saída**: O arquivo Markdown (.md) gerado a partir de um Arquivo_Fonte
- **Pasta_Destino**: O diretório escolhido pelo Usuário onde os Arquivos_Saída serão salvos
- **Subpasta_Assets**: Subpasta criada dentro da Pasta_Destino para armazenar imagens e objetos extraídos de um Arquivo_Fonte
- **Objeto_Embutido**: Imagem, diagrama ou outro elemento não-textual contido em um Arquivo_Fonte
- **Seletor_Arquivos**: Diálogo nativo do sistema operacional para selecionar arquivos ou pastas
- **Barra_Progresso**: Indicador visual que mostra o andamento da conversão
- **Conversor**: Módulo responsável por transformar o conteúdo do PDF em formato Markdown
- **OCR**: Reconhecimento Óptico de Caracteres (Optical Character Recognition) — técnica que extrai texto a partir de imagens
- **Motor_OCR**: Biblioteca ou serviço que executa o reconhecimento óptico de caracteres em uma imagem ou página de PDF
- **PDF_Imagem**: Arquivo PDF cujas páginas são compostas por imagens digitalizadas (escaneadas) sem camada de texto extraível
- **Markdown_Ilegível**: Arquivo_Saída gerado a partir de um PDF_Imagem que está vazio ou contém apenas caracteres sem sentido, indicando falha na extração de texto convencional
- **Fallback_OCR**: Processo de reprocessamento de PDFs_Imagem utilizando OCR após detecção de Markdown_Ilegível
- **Seção_Sobre**: Área da Aplicação que exibe informações sobre o autor, licença e links relevantes do projeto
- **README**: Arquivo de documentação principal do repositório, contendo instruções de instalação e uso
- **Licença_Open_Source**: Licença de software que permite distribuição, uso e modificação do código-fonte
- **Tutorial_Instalação**: Guia passo a passo para instalação da Aplicação em diferentes sistemas operacionais
- **Idioma_Interface**: Língua utilizada nos textos, rótulos, mensagens e diálogos da interface gráfica da Aplicação
- **Seletor_Idioma**: Componente da interface que permite ao Usuário escolher entre os idiomas disponíveis (Português BR ou Inglês)
- **i18n**: Internacionalização — processo de projetar a Aplicação para suportar múltiplos idiomas

## Requirements

### Requirement 1: Seleção de Arquivos PDF

**User Story:** Como Usuário, quero selecionar múltiplos arquivos PDF de uma pasta, para que eu possa converter vários documentos de uma vez.

#### Acceptance Criteria

1. WHEN o Usuário acionar a função de seleção de arquivos, THE Aplicação SHALL abrir o Seletor_Arquivos nativo do sistema operacional com filtro para arquivos PDF (.pdf)
2. WHEN o Usuário selecionar um ou mais arquivos PDF no Seletor_Arquivos, THE Aplicação SHALL exibir a lista de arquivos selecionados com nome, caminho completo e tamanho do arquivo, limitando a seleção a no máximo 50 arquivos por operação
3. WHEN o Usuário selecionar arquivos, THE Aplicação SHALL permitir adicionar ou remover arquivos individuais da lista antes de iniciar a conversão
4. IF o Usuário não selecionar nenhum arquivo e tentar iniciar a conversão, THEN THE Aplicação SHALL exibir uma mensagem informando que é necessário selecionar ao menos um arquivo
5. IF o Usuário selecionar um arquivo que não é um PDF válido (arquivo corrompido ou com extensão .pdf mas formato inválido), THEN THE Aplicação SHALL excluir o arquivo da lista e exibir uma mensagem indicando quais arquivos foram rejeitados por serem inválidos
6. IF o Usuário tentar adicionar um arquivo que já está presente na lista de seleção, THEN THE Aplicação SHALL ignorar a duplicação e manter apenas uma entrada do arquivo na lista

### Requirement 2: Seleção da Pasta de Destino

**User Story:** Como Usuário, quero escolher a pasta de destino dos arquivos convertidos, para que eu possa organizar os arquivos Markdown onde preferir.

#### Acceptance Criteria

1. WHEN o Usuário acionar a função de seleção de pasta de destino, THE Aplicação SHALL abrir o Seletor_Arquivos nativo do sistema operacional no modo de seleção de diretório
2. WHEN o Usuário selecionar uma pasta de destino, THE Aplicação SHALL exibir o caminho completo da Pasta_Destino selecionada
3. IF o Usuário não selecionar uma Pasta_Destino e tentar iniciar a conversão, THEN THE Aplicação SHALL exibir uma mensagem informando que é necessário selecionar uma pasta de destino
4. IF a Pasta_Destino selecionada não possuir permissão de escrita, THEN THE Aplicação SHALL exibir uma mensagem de erro informando que não há permissão para gravar na pasta selecionada
5. IF o Usuário cancelar o diálogo de seleção de pasta, THEN THE Aplicação SHALL manter a Pasta_Destino anteriormente selecionada (ou vazia, caso nenhuma tenha sido escolhida)

### Requirement 3: Conversão de PDF para Markdown

**User Story:** Como Usuário, quero converter os PDFs selecionados em arquivos Markdown, para que eu possa utilizar o conteúdo textual dos documentos em formato leve e editável.

#### Acceptance Criteria

1. WHEN o Usuário iniciar a conversão, THE Conversor SHALL processar cada Arquivo_Fonte sequencialmente, gerar um Arquivo_Saída em formato Markdown na Pasta_Destino e exibir o progresso indicando o arquivo atual e a quantidade de arquivos processados em relação ao total
2. THE Conversor SHALL nomear cada Arquivo_Saída com o mesmo nome do Arquivo_Fonte correspondente, substituindo a extensão .pdf por .md
3. WHEN o Conversor processar um Arquivo_Fonte, THE Conversor SHALL preservar a estrutura hierárquica do documento (títulos, subtítulos, parágrafos, listas e tabelas) no formato Markdown equivalente
4. WHEN o Conversor processar um Arquivo_Fonte que contenha tabelas, THE Conversor SHALL converter as tabelas para o formato de tabelas Markdown
5. IF um Arquivo_Fonte estiver corrompido, protegido por senha ou contiver apenas imagens sem texto extraível, THEN THE Conversor SHALL exibir uma mensagem ao Usuário identificando o arquivo e o motivo da falha, e continuar processando os demais arquivos da lista
6. IF já existir um Arquivo_Saída com o mesmo nome na Pasta_Destino, THEN THE Aplicação SHALL perguntar ao Usuário se deseja sobrescrever o arquivo existente
7. WHEN o Conversor finalizar o processamento de todos os Arquivos_Fonte, THE Conversor SHALL exibir um resumo ao Usuário contendo a quantidade de arquivos convertidos com sucesso e a quantidade de arquivos que falharam

### Requirement 4: Extração de Imagens e Objetos Embutidos

**User Story:** Como Usuário, quero ter a opção de extrair imagens e objetos embutidos dos PDFs, para que eu possa preservar todo o conteúdo visual dos documentos originais.

#### Acceptance Criteria

1. THE Aplicação SHALL exibir uma opção habilitável para extrair Objetos_Embutidos durante a conversão
2. WHILE a opção de extração de Objetos_Embutidos estiver habilitada, WHEN o Conversor processar um Arquivo_Fonte, THE Conversor SHALL extrair todas as imagens e objetos embutidos para a Subpasta_Assets, criada no mesmo diretório do Arquivo_Saída
3. THE Conversor SHALL nomear a Subpasta_Assets com o mesmo nome base do Arquivo_Fonte (sem extensão) seguido do sufixo "_assets"
4. WHEN o Conversor extrair um Objeto_Embutido, THE Conversor SHALL salvar o objeto no formato original (PNG, JPEG, SVG ou outro formato detectado) com nome sequencial composto por "img_" seguido de número incremental com 3 dígitos (ex.: img_001.png, img_002.jpeg)
5. WHILE a opção de extração de Objetos_Embutidos estiver habilitada, WHEN o Conversor gerar o Arquivo_Saída, THE Conversor SHALL inserir referências Markdown no formato `![imageN](caminho_relativo)` no local correspondente à posição do objeto na página do PDF original
6. WHILE a opção de extração de Objetos_Embutidos estiver desabilitada, WHEN o Conversor encontrar um Objeto_Embutido, THE Conversor SHALL ignorar o objeto e continuar a conversão apenas do conteúdo textual
7. IF a extração de um Objeto_Embutido específico falhar, THEN THE Conversor SHALL registrar o erro no log, inserir um marcador textual indicando falha na extração na posição correspondente do Arquivo_Saída, e continuar processando os demais objetos
8. WHILE a opção de extração de Objetos_Embutidos estiver habilitada, IF o Arquivo_Fonte não contiver nenhum Objeto_Embutido extraível, THEN THE Conversor SHALL gerar o Arquivo_Saída normalmente sem criar a Subpasta_Assets

### Requirement 5: Indicação de Progresso

**User Story:** Como Usuário, quero visualizar o progresso da conversão, para que eu saiba quanto tempo falta para a operação ser concluída.

#### Acceptance Criteria

1. WHILE a conversão estiver em andamento, THE Aplicação SHALL atualizar a Barra_Progresso a cada arquivo concluído, indicando a porcentagem de arquivos já processados em relação ao total
2. WHILE a conversão estiver em andamento, THE Aplicação SHALL exibir o nome do Arquivo_Fonte sendo processado no momento, truncando nomes com mais de 60 caracteres com reticências
3. WHEN a conversão de todos os arquivos for concluída, THE Aplicação SHALL exibir um resumo contendo o número de arquivos convertidos com sucesso e o número de falhas
4. IF um arquivo individual falhar durante a conversão, THEN THE Aplicação SHALL continuar a conversão dos demais arquivos e incrementar a Barra_Progresso normalmente

### Requirement 6: Compatibilidade Multiplataforma

**User Story:** Como Usuário, quero utilizar a aplicação tanto no Linux quanto no Windows, para que eu possa trabalhar em qualquer um dos meus ambientes.

#### Acceptance Criteria

1. THE Aplicação SHALL executar todas as funcionalidades de conversão em sistemas operacionais Linux (distribuições com suporte a Python 3.10 ou superior) e Windows (10 ou superior), sem diferenças de comportamento observável entre plataformas
2. THE Aplicação SHALL utilizar diálogos nativos do sistema operacional para seleção de arquivos e pastas
3. THE Aplicação SHALL resolver separadores de caminho de arquivo de acordo com o sistema operacional em execução (barra "/" no Linux e barra invertida "\\" no Windows), permitindo leitura e escrita de arquivos em caminhos que contenham espaços e caracteres acentuados
4. THE Aplicação SHALL gerar Arquivos_Saída com codificação UTF-8 e terminadores de linha LF (\n) em ambos os sistemas operacionais

### Requirement 7: Interface Gráfica Desktop

**User Story:** Como Usuário, quero uma interface gráfica simples e intuitiva, para que eu possa realizar as conversões sem precisar usar linha de comando.

#### Acceptance Criteria

1. THE Aplicação SHALL apresentar uma janela principal contendo: área de listagem de arquivos selecionados, botão para abrir diálogo de seleção de arquivos PDF, campo exibindo a Pasta_Destino com botão para alterar a pasta via diálogo de seleção de diretório, opção de extração de Objetos_Embutidos e botão para iniciar a conversão
2. WHEN a conversão anterior for concluída com sucesso ou com erro, THE Aplicação SHALL reabilitar o botão de iniciar conversão e permitir que o Usuário inicie uma nova conversão sem precisar reiniciar a Aplicação
3. WHILE a conversão estiver em andamento, THE Aplicação SHALL desabilitar o botão de iniciar conversão e exibir um indicador de progresso visível ao Usuário
4. WHILE o processamento de arquivos estiver em andamento, THE Aplicação SHALL responder a interações do Usuário (como mover ou redimensionar a janela) em no máximo 500 milissegundos
5. IF o Usuário acionar o botão de iniciar conversão sem nenhum arquivo na lista de seleção, THEN THE Aplicação SHALL exibir uma mensagem informando que é necessário selecionar ao menos um arquivo e não iniciar o processamento
6. WHEN a conversão de todos os arquivos for concluída, THE Aplicação SHALL exibir um resumo indicando a quantidade de arquivos convertidos com sucesso e a quantidade de arquivos com falha

### Requirement 8: Fallback OCR para PDFs Baseados em Imagem

**User Story:** Como Usuário, quero que a aplicação detecte PDFs que produziram Markdown ilegível (por serem imagens escaneadas) e me ofereça a opção de reprocessá-los com OCR, para que eu consiga extrair texto mesmo de documentos digitalizados.

#### Acceptance Criteria

1. WHEN o Conversor finalizar o processamento de todos os Arquivos_Fonte do batch, THE Aplicação SHALL analisar cada Arquivo_Saída gerado e identificar quais produziram Markdown_Ilegível (conteúdo vazio ou com menos de 50 caracteres alfanuméricos por página)
2. WHEN a Aplicação detectar um ou mais PDFs_Imagem no batch processado, THE Aplicação SHALL exibir ao Usuário uma lista contendo os nomes dos arquivos que necessitam de OCR, informando que esses arquivos parecem ser documentos escaneados
3. WHEN a Aplicação notificar o Usuário sobre PDFs_Imagem detectados, THE Aplicação SHALL perguntar ao Usuário se deseja reprocessar esses arquivos utilizando Fallback_OCR
4. WHEN o Usuário confirmar o reprocessamento com OCR, THE Aplicação SHALL executar o Motor_OCR primário (Tesseract) em cada PDF_Imagem identificado, extrair o texto reconhecido e converter o resultado para formato Markdown, substituindo o Arquivo_Saída anterior
5. IF o Motor_OCR primário falhar na extração de texto legível de um PDF_Imagem (resultado com menos de 50 caracteres alfanuméricos por página), THEN THE Aplicação SHALL tentar um Motor_OCR secundário (EasyOCR) no mesmo arquivo
6. IF todos os Motores_OCR disponíveis falharem na extração de texto de um PDF_Imagem, THEN THE Aplicação SHALL informar ao Usuário que o arquivo não pôde ser convertido por nenhuma técnica de OCR disponível e manter o Arquivo_Saída original
7. WHILE o Fallback_OCR estiver em andamento, THE Aplicação SHALL exibir a Barra_Progresso indicando o arquivo sendo processado e a quantidade de arquivos de OCR processados em relação ao total de PDFs_Imagem
8. WHEN o Fallback_OCR finalizar o processamento de todos os PDFs_Imagem, THE Aplicação SHALL exibir um resumo ao Usuário contendo a quantidade de arquivos recuperados com sucesso via OCR, a quantidade de falhas e qual Motor_OCR foi utilizado em cada arquivo
9. IF o Usuário recusar o reprocessamento com OCR, THEN THE Aplicação SHALL manter os Arquivos_Saída originais inalterados e encerrar o fluxo de conversão normalmente

### Requirement 9: Sobre, Licenciamento e Tutorial de Instalação

**User Story:** Como Usuário, quero acessar informações sobre o autor, a licença do software e um guia de instalação, para que eu saiba quem desenvolveu a aplicação, quais são os termos de uso e como instalá-la corretamente.

#### Acceptance Criteria

1. THE Aplicação SHALL exibir um item de menu ou botão "Sobre" que, ao ser acionado, abre a Seção_Sobre contendo o nome do autor (William Mendes), link para o perfil GitHub (http://github.com/wcmendes) e link para o currículo Lattes (https://lattes.cnpq.br/7726054867638395)
2. THE Aplicação SHALL incluir uma Licença_Open_Source válida (MIT ou equivalente) no repositório do projeto, permitindo distribuição, uso e modificação do código-fonte
3. THE Aplicação SHALL disponibilizar um README no repositório contendo: descrição do projeto, requisitos do sistema, Tutorial_Instalação passo a passo, instruções de uso e informações de licença
4. THE Aplicação SHALL disponibilizar o README em dois idiomas: Português (Brasil) no arquivo README.md e Inglês no arquivo README_EN.md
5. WHEN o Usuário abrir a Seção_Sobre, THE Aplicação SHALL exibir a versão atual da Aplicação e o ano de publicação
6. WHEN o Usuário clicar em um link na Seção_Sobre (GitHub ou Lattes), THE Aplicação SHALL abrir o link no navegador padrão do sistema operacional

### Requirement 10: Internacionalização (Português e Inglês)

**User Story:** Como Usuário, quero poder utilizar a interface da aplicação em Português (Brasil) ou Inglês, para que eu possa operar o software no idioma de minha preferência.

#### Acceptance Criteria

1. THE Aplicação SHALL suportar dois idiomas de interface: Português (Brasil) como idioma padrão e Inglês (US)
2. THE Aplicação SHALL exibir um Seletor_Idioma na interface principal que permite ao Usuário alternar entre Português (Brasil) e Inglês
3. WHEN o Usuário selecionar um idioma no Seletor_Idioma, THE Aplicação SHALL atualizar todos os textos visíveis da interface (rótulos de botões, mensagens de erro, mensagens de progresso, resumos e diálogos) para o idioma selecionado sem necessidade de reiniciar a Aplicação
4. THE Aplicação SHALL persistir a preferência de idioma do Usuário localmente, de modo que ao reabrir a Aplicação o último idioma selecionado seja restaurado automaticamente
5. WHEN a Aplicação for iniciada pela primeira vez sem preferência salva, THE Aplicação SHALL utilizar Português (Brasil) como Idioma_Interface padrão
6. THE Aplicação SHALL manter a consistência linguística completa em cada idioma, garantindo que nenhum texto da interface permaneça em idioma diferente do selecionado pelo Usuário
