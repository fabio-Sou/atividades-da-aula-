# Painel S1 local para Windows

O aplicativo permite usar uma imagem fixa ou percorrer imagens PNG, GIF e
JPEG (`.jpg`/`.jpeg`) de uma pasta no painel físico `04D9:FD01`. Mostra CPU,
RAM, relógio, tempo ligado e disco no painel e uma prévia ilustrativa fixa na
janela.

## Abrir

Dê dois cliques em `iniciar.bat`. É necessário Python para Windows com Tkinter
e Python Launcher (incluindo `pyw`), normalmente incluídos na instalação
padrão, além das dependências Pillow e pystray. O iniciador abre o app sem
manter uma janela de CMD/PowerShell aberta. Se Pillow ou pystray estiverem
faltando, o `.bat` tenta instalá-los automaticamente com `pip`; nessa primeira
execução, é necessária uma conexão com a internet.
Somente uma instância do Painel S1 pode ser aberta por vez para evitar
concorrência pelo dispositivo USB.

O app mantém um ícone na bandeja do sistema. Minimizar a janela ou clicar no
botão **X** a oculta na bandeja, sem parar a atualização contínua. Clique duas
vezes no ícone ou use **Abrir Painel S1** para restaurar a janela. Para encerrar
o aplicativo, escolha **Sair** no menu do ícone.

## Uso

1. Abra `iniciar.bat`.
2. Escolha **Imagem fixa** e selecione um PNG, GIF ou JPEG, ou escolha
   **Alternar imagens de uma pasta** e selecione a pasta. A primeira seleção
   é preparada em segundo plano; no caso de uma pasta, o app prepara todas as
   imagens antes de liberar o início e mostra o progresso.
3. Selecione o ajuste desejado: **Preencher** recorta para cobrir a tela,
   **Ajustar** mantém a imagem inteira com faixas quando necessário,
   **Estender** distorce para ocupar a tela, **Lado a lado** repete no tamanho
   original, **Centralizar** mantém o tamanho original e recorta excedentes,
   e **Ampliar** amplia proporcionalmente para cobrir a tela (igual a
   Preencher em uma única tela).
4. Escolha a orientação **Deitada** ou **Em pé**. A prévia acompanha a
   orientação, e a seleção é enviada ao firmware junto com o próximo quadro.
5. Use **Personalizar informações...** para ativar/desativar CPU, RAM,
   relógio/data, tempo ligado e espaço em disco. Para cada informação, escolha
   uma posição e um tamanho (**Normal**, **Grande** ou **Extra grande**), ou
   arraste-a diretamente na prévia. Essa edição fica bloqueada durante a
   atualização contínua.
6. Selecione o **Intervalo das imagens da pasta** antes de iniciar: há opções
   de 10 a 300 segundos, incluindo 15 e 30 segundos. O intervalo se refere ao
   tempo entre o início de cada envio de imagem; um quadro completo leva cerca
   de nove segundos para ser aceito.
7. Clique em **Iniciar atualização contínua** e confirme. O app envia a imagem
   escolhida e mantém as métricas atualizadas somente na tela física. Os
   valores mostrados na prévia da janela são demonstrativos e não mudam.
8. Durante o modo contínuo, **Escolher imagem...** mostra a nova imagem na
   prévia e a envia automaticamente após a seleção; as métricas continuam
   atualizando. Alterar o ajuste também aplica a nova composição ao painel.
9. **Teste visual S1 TEST** envia um padrão azul de diagnóstico, sem depender
   da imagem ou das métricas. Ele substitui o conteúdo atual da tela.
10. Clique em **Parar** para encerrar atualizações automáticas. Se um quadro
   estiver sendo enviado, ele termina antes de parar.

A aba **Biblioteca** guarda imagens e pastas usadas anteriormente. A lista tem
contraste escuro e seleção destacada; selecione um item e use **Usar
selecionado** (ou dê duplo clique) para carregá-lo novamente; **Remover da
biblioteca...** apaga o registro e as cópias preparadas, nunca o arquivo ou a
pasta original. O app cria `Imagens preparadas` ao lado dos arquivos do
programa: `Imagens visuais` contém cópias PNG identificáveis pelo nome original
e prontas na resolução/orientação selecionada; `Dados internos` contém os
pixels preparados usados diretamente no envio. O cache é reutilizado enquanto
o arquivo original, o ajuste e a orientação não mudarem. Uma mudança nesses
itens faz o app preparar uma nova versão.

O modo contínuo envia um quadro completo imediatamente. Com imagem fixa,
atualiza as áreas de CPU, RAM, relógio e tempo ligado a cada 0,8 segundo, sem
reenviar o fundo. No modo pasta, percorre as imagens em ordem alfabética,
repete a lista e troca o quadro completo no intervalo selecionado; as áreas de
métricas continuam sendo atualizadas a cada 0,8 segundo. Um quadro completo leva
cerca de nove segundos para ser aceito, mas a atualização parcial das métricas
não precisa esperar esse intervalo. O modo contínuo não começa ao abrir o app:
é preciso clicar em Iniciar e confirmar.
Depois do primeiro envio, enquanto o app estiver aberto, ele também envia um
sinal de horário a cada 1,6 segundo para manter a comunicação; esse sinal não
altera a imagem. Para atualizar métricas e imagens continuamente, use o modo
contínuo.

## Segurança e limitações

- O app usa o driver HID atual do Windows. Mantém a conexão aberta enquanto o
  app está rodando para evitar abrir/fechar o dispositivo a cada quadro. Não
  instala, remove ou troca drivers e não precisa reiniciar o computador.
- A detecção do painel é somente leitura. Atualizações automáticas começam só
  após confirmação e param se ocorrer erro. Durante o modo contínuo, escolher
  uma imagem a envia para o painel depois da seleção.
- Um quadro completo demora cerca de nove segundos. Evite iniciar outro
  programa de controle da telinha ao mesmo tempo.
- A leitura de CPU usa o contador agregado de desempenho do Windows,
  especificamente `% Processor Utility`, que acompanha melhor a utilização
  exibida pelo Gerenciador de Tarefas do que `% Processor Time`. As métricas
  reais são consultadas a cada 0,8 segundo somente durante o modo contínuo; parado,
  o app mantém uma leitura inicial para verificar disponibilidade e só tenta
  novamente a cada cinco segundos se essa leitura falhar. No modo contínuo,
  apenas pixels alterados são enviados pelo comando de atualização parcial do
  painel.
- As métricas são consultadas localmente por APIs do Windows. O app não abre
  portas de rede, não acessa a internet nem grava histórico de métricas.
- Temperatura da CPU e RPM da ventoinha não são incluídos porque este PC não
  os expõe pelas interfaces padrão WMI do Windows. O app não instala nem usa
  `GetCPUInfo.sys`, WinRing0 ou drivers de sensores.
- A prévia reflete os seis modos de ajuste e aplica a mesma composição enviada
  ao painel. O modo selecionado, os caminhos da última imagem e pasta, o ajuste,
  a orientação, o intervalo e as preferências de visibilidade/posição são
  salvos localmente em `%USERPROFILE%\.painel_s1_windows.json`. Ao reabrir, a
  última seleção e os dados do cache são restaurados pelas preferências, sem
  criar um novo registro na Biblioteca; a atualização contínua permanece parada
  até o usuário iniciá-la. A janela principal tem rolagem vertical
  quando o conteúdo excede a altura disponível.
- A prévia mantém valores ilustrativos fixos (CPU 65%, RAM 20% e outros
  exemplos); ela nunca exibe as leituras reais do computador. A tela física
  recebe as métricas reais durante o modo contínuo. O título decorativo não é
  enviado à tela.

## Referências

- [Notas do protocolo do painel S1](https://github.com/nov30th/s1-mini-computer-tft-screen-release/blob/source-code/docs/protocol.md)
- [Implementação de referência para Linux](https://github.com/nov30th/s1-mini-computer-tft-screen-release/tree/source-code)
- [Pacote de sincronização de horário usado como heartbeat](https://github.com/tjaworski/AceMagic-S1-LED-TFT-Linux/blob/main/s1panel/lcd_device.js)
- [Configuração de referência com intervalo de atualização de 1,6 s](https://github.com/tjaworski/AceMagic-S1-LED-TFT-Linux/blob/main/s1panel/config.json)

O guia de temas Piero24 inclui uma configuração de servidor web escutando em
`0.0.0.0:8686`. Este app não inicia servidor nem abre portas de rede.
