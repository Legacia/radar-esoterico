from datetime import date
from decimal import Decimal as D

from radar.fornecedores import salvar_fornecedor
from radar.produtos import registrar_cotacao, salvar_produto


def criar_base(db):
    fornecedor = salvar_fornecedor("Fornecedor fictício do Bloco 3", "CNPJ fictício", "Contato fictício",
        D(0),"5 dias","Pix",True,True,True,True,True,caminho=db)
    produto = salvar_produto("Produto fictício A","Incensos","Candidato",True,True,True,caminho=db)
    cotacao = registrar_cotacao(fornecedor,produto,"FICTICIO-A",D(20),1,date.today(),D("59.90"),db)
    return fornecedor, produto, cotacao
