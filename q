warning: in the working copy of 'Atividade-Avaliativa/modulo2.ipynb', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'Atividade-Avaliativa/nota(1).ipynb', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/Atividade-Avaliativa/modulo2.ipynb b/Atividade-Avaliativa/modulo2.ipynb[m
[1mindex 016b3e4..fd8d044 100644[m
[1m--- a/Atividade-Avaliativa/modulo2.ipynb[m
[1m+++ b/Atividade-Avaliativa/modulo2.ipynb[m
[36m@@ -181,7 +181,7 @@[m
         },[m
         {[m
             "cell_type": "code",[m
[31m-            "execution_count": 8,[m
[32m+[m[32m            "execution_count": null,[m
             "id": "ea709d04",[m
             "metadata": {},[m
             "outputs": [[m
[36m@@ -196,7 +196,7 @@[m
             "source": [[m
                 "# Questão 7\n",[m
                 "\n",[m
[31m-                "p1 = input(\"Por favor, digite a 1ª palavra: \").strip()\n",[m
[32m+[m[32m                "p1 = input(\"Por favor, digite a 1ª palavra: \").strip() \n",[m
                 "p2 = input(\"Por favor, digite a 2ª palavra: \").strip()\n",[m
                 "\n",[m
                 "if p1 == p2:\n",[m
[1mdiff --git a/Atividade-Avaliativa/nota(1).ipynb b/Atividade-Avaliativa/nota(1).ipynb[m
[1mindex eaf88db..826d32b 100644[m
[1m--- a/Atividade-Avaliativa/nota(1).ipynb[m
[1m+++ b/Atividade-Avaliativa/nota(1).ipynb[m
[36m@@ -2,7 +2,7 @@[m
  "cells": [[m
   {[m
    "cell_type": "code",[m
[31m-   "execution_count": 15,[m
[32m+[m[32m   "execution_count": 19,[m
    "id": "be23f142",[m
    "metadata": {},[m
    "outputs": [[m
[36m@@ -12,7 +12,7 @@[m
      "text": [[m
       "OLÁ, MUNDO!\n",[m
       "olá, mundo!\n",[m
[31m-      "Olá ,  Mundo!\n",[m
[32m+[m[32m      "Olá, Mundo!\n",[m
       "0\n",[m
       "J\n",[m
       "Joã\n"[m
[36m@@ -22,7 +22,7 @@[m
    "source": [[m
     "# uma sequ\n",[m
     "nome = \"João\"\n",[m
[31m-    "nome2 = \"Olá ,  Mundo!\"\n",[m
[32m+[m[32m    "nome2 = \" Olá, Mundo! \"\n",[m
     "print(\"Olá, Mundo!\".upper())\n",[m
     "print(\"Olá, Mundo!\".lower())\n",[m
     "limpo = nome2.strip(\" \") # remove espaços em branco no início e no final \n",[m
[36m@@ -34,26 +34,47 @@[m
   },[m
   {[m
    "cell_type": "code",[m
[31m-   "execution_count": 16,[m
[32m+[m[32m   "execution_count": null,[m
    "id": "3d805db8",[m
    "metadata": {},[m
    "outputs": [[m
     {[m
[31m-     "ename": "AttributeError",[m
[31m-     "evalue": "'tuple' object has no attribute 'split'",[m
[31m-     "output_type": "error",[m
[31m-     "traceback": [[m
[31m-      "\u001b[31m---------------------------------------------------------------------------\u001b[39m",[m
[31m-      "\u001b[31mAttributeError\u001b[39m                            Traceback (most recent call last)",[m
[31m-      "\u001b[36mCell\u001b[39m\u001b[36m \u001b[39m\u001b[32mIn[16]\u001b[39m\u001b[32m, line 2\u001b[39m\n\u001b[32m      1\u001b[39m cores = \u001b[33m\"azul\"\u001b[39m, \u001b[33m\"vermelho\"\u001b[39m, \u001b[33m\"verde\"\u001b[39m\n\u001b[32m----> \u001b[39m\u001b[32m2\u001b[39m print(cores.split(\u001b[33m\",\"\u001b[39m))\n",[m
[31m-      "\u001b[31mAttributeError\u001b[39m: 'tuple' object has no attribute 'split'"[m
[32m+[m[32m     "name": "stdout",[m
[32m+[m[32m     "output_type": "stream",[m
[32m+[m[32m     "text": [[m
[32m+[m[32m      "['azul', 'vermelho', 'verde']\n"[m
      ][m
     }[m
    ],[m
    "source": [[m
[31m-    "cores = \"azul\", \"vermelho\", \"verde\"\n",[m
[32m+[m[32m    "cores = \"azul,vermelho,verde\"\n",[m
     "print(cores.split(\",\"))"[m
    ][m
[32m+[m[32m  },[m
[32m+[m[32m  {[m
[32m+[m[32m   "cell_type": "code",[m
[32m+[m[32m   "execution_count": 23,[m
[32m+[m[32m   "id": "d748bc0b",[m
[32m+[m[32m   "metadata": {},[m
[32m+[m[32m   "outputs": [[m
[32m+[m[32m    {[m
[32m+[m[32m     "name": "stdout",[m
[32m+[m[32m     "output_type": "stream",[m
[32m+[m[32m     "text": [[m
[32m+[m[32m      "fabio\n",[m
[32m+[m[32m      "FABIO\n",[m
[32m+[m[32m      "Nome = fabio\n",[m
[32m+[m[32m      "Caracteres = 5\n"[m
[32m+[m[32m     ][m
[32m+[m[32m    }[m
[32m+[m[32m   ],[m
[32m+[m[32m   "source": [[m
[32m+[m[32m    "nome = input(\"Digite seu nome: \")\n",[m
[32m+[m[32m    "print(nome.strip()) # remove espaços em branco no início e no final\n",[m
[32m+[m[32m    "print(nome.upper()) # transforma em maiúsculo\n",[m
[32m+[m[32m    "print(\"Nome =\", nome)\n",[m
[32m+[m[32m    "print(\"Caracteres =\", len(nome))"[m
[32m+[m[32m   ][m
   }[m
  ],[m
  "metadata": {[m
[36m@@ -72,7 +93,7 @@[m
    "name": "python",[m
    "nbconvert_exporter": "python",[m
    "pygments_lexer": "ipython3",[m
[31m-   "version": "3.15.0rc2"[m
[32m+[m[32m   "version": "3.15.0"[m
   }[m
  },[m
  "nbformat": 4,[m
