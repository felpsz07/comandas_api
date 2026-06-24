from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from domain.schemas.RecebimentoSchema import (
    RecebimentoDashboardItem, ComandaDetalheRecebimento,
    RecebimentoCompletoRequest, RecebimentoCompletoResponse, ComandaPagaResponse,
    ComprovanteRecebimento, ComprovanteCabecalho, ComprovanteComandaItem,
    ComprovanteResumoValores, ComprovanteRecebimentoInfo, ComprovanteRodape
)
from domain.schemas.ComandaSchema import (
    FuncionarioResponse, ClienteResponse, ComandaProdutosResponse, ProdutoResponse
)
from domain.schemas.AuthSchema import FuncionarioAuth

from infra.orm.RecebimentoModel import RecebimentoDB, RecebimentoComandaDB
from infra.orm.ComandaModel import ComandaDB, ComandaProdutoDB
from infra.orm.ProdutoModel import ProdutoDB
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.orm.ClienteModel import ClienteDB
from infra.database import get_async_db
from infra.dependencies import require_group, get_current_active_user
from infra.rate_limit import limiter
from services.AuditoriaService import AuditoriaService

router = APIRouter()


# ── Helper interno: monta os itens de uma comanda já com produto/funcionário ──
async def _montar_itens_comanda(db: AsyncSession, comanda_id: int) -> List[ComandaProdutosResponse]:
    produtos_query = (
        select(ComandaProdutoDB, ProdutoDB, FuncionarioDB)
        .outerjoin(ProdutoDB, ComandaProdutoDB.produto_id == ProdutoDB.id)
        .outerjoin(FuncionarioDB, ComandaProdutoDB.funcionario_id == FuncionarioDB.id)
        .where(ComandaProdutoDB.comanda_id == comanda_id)
    )
    result = await db.execute(produtos_query)
    rows = result.all()

    itens = []
    for comanda_produto, produto, funcionario in rows:
        produto_response = ProdutoResponse(
            id=produto.id, nome=produto.nome, descricao=produto.descricao,
            foto=produto.foto, valor_unitario=produto.valor_unitario
        ) if produto else None

        funcionario_response = FuncionarioResponse(
            id=funcionario.id, nome=funcionario.nome, matricula=funcionario.matricula,
            cpf=funcionario.cpf, telefone=funcionario.telefone, grupo=funcionario.grupo
        ) if funcionario else None

        itens.append(ComandaProdutosResponse(
            id=comanda_produto.id,
            comanda_id=comanda_produto.comanda_id,
            funcionario_id=comanda_produto.funcionario_id,
            funcionario=funcionario_response,
            produto_id=comanda_produto.produto_id,
            produto=produto_response,
            quantidade=comanda_produto.quantidade,
            valor_unitario=comanda_produto.valor_unitario
        ))

    return itens


def _funcionario_to_response(funcionario: FuncionarioDB) -> FuncionarioResponse:
    return FuncionarioResponse(
        id=funcionario.id, nome=funcionario.nome, matricula=funcionario.matricula,
        cpf=funcionario.cpf, telefone=funcionario.telefone, grupo=funcionario.grupo
    )


def _cliente_to_response(cliente: ClienteDB) -> ClienteResponse:
    return ClienteResponse(id=cliente.id, nome=cliente.nome, cpf=cliente.cpf, telefone=cliente.telefone)


# ── 1. Dashboard com todas as comandas abertas ────────────────────────────────
@router.get(
    "/recebimento/dashboard",
    response_model=List[RecebimentoDashboardItem],
    tags=["Recebimento"],
    summary="Dashboard completo com comandas abertas - protegida por JWT e grupo 1 ou 3"
)
@limiter.limit("moderate")
async def get_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    try:
        query = (
            select(ComandaDB, ClienteDB)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
            .where(ComandaDB.status == 0)
            .order_by(ComandaDB.data_hora.asc())
        )
        result = await db.execute(query)
        rows = result.all()

        dashboard = []
        for comanda, cliente in rows:
            itens = await _montar_itens_comanda(db, comanda.id)
            total = sum(float(item.valor_unitario) * item.quantidade for item in itens)
            quantidade_produtos = sum(item.quantidade for item in itens)

            dashboard.append(RecebimentoDashboardItem(
                id=comanda.id,
                comanda=comanda.comanda,
                status=comanda.status,
                cliente=_cliente_to_response(cliente) if cliente else None,
                total=round(total, 2),
                quantidade_produtos=quantidade_produtos,
                data_hora=comanda.data_hora
            ))

        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao buscar dashboard: {str(e)}")


# ── 2. Detalhe de uma ou mais comandas para conferência ───────────────────────
@router.get(
    "/recebimento/comandas/detalhe/{comandas_ids}",
    response_model=List[ComandaDetalheRecebimento],
    tags=["Recebimento"],
    summary="Detalhar comandas para recebimento - protegida por JWT e grupo 1 ou 3"
)
@limiter.limit("moderate")
async def get_comandas_detalhe(
    comandas_ids: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    try:
        # comandas_ids vem como string separada por vírgula na URL, ex: "1,2,3"
        try:
            ids = [int(i.strip()) for i in comandas_ids.split(",") if i.strip()]
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="IDs de comandas inválidos. Use números separados por vírgula")

        if not ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum ID de comanda informado")

        query = (
            select(ComandaDB, ClienteDB)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
            .where(ComandaDB.id.in_(ids))
        )
        result = await db.execute(query)
        rows = result.all()

        encontrados_ids = {comanda.id for comanda, _ in rows}
        faltantes = set(ids) - encontrados_ids
        if faltantes:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comanda(s) não encontrada(s): {sorted(faltantes)}")

        detalhes = []
        for comanda, cliente in rows:
            itens = await _montar_itens_comanda(db, comanda.id)
            total = sum(float(item.valor_unitario) * item.quantidade for item in itens)
            quantidade_produtos = sum(item.quantidade for item in itens)

            detalhes.append(ComandaDetalheRecebimento(
                id=comanda.id,
                comanda=comanda.comanda,
                status=comanda.status,
                cliente=_cliente_to_response(cliente) if cliente else None,
                itens=itens,
                total=round(total, 2),
                quantidade_produtos=quantidade_produtos,
                data_hora=comanda.data_hora
            ))

        return detalhes
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao buscar detalhe das comandas: {str(e)}")


# ── 3. Recebimento completo (fecha N comandas em uma única operação atômica) ──
@router.post(
    "/recebimento/completo",
    response_model=RecebimentoCompletoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Recebimento"],
    summary="Recebimento completo com desconto/acréscimo - protegida por JWT e grupo 1 ou 3"
)
@limiter.limit("restrictive")
async def recebimento_completo(
    recebimento_data: RecebimentoCompletoRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    try:
        # Buscar todas as comandas informadas de uma vez
        query = select(ComandaDB).where(ComandaDB.id.in_(recebimento_data.comandas_ids))
        result = await db.execute(query)
        comandas = result.scalars().all()

        encontrados_ids = {c.id for c in comandas}
        faltantes = set(recebimento_data.comandas_ids) - encontrados_ids
        if faltantes:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comanda(s) não encontrada(s): {sorted(faltantes)}")

        # Validar status de TODAS as comandas antes de processar qualquer uma (atomicidade lógica)
        for comanda in comandas:
            if comanda.status == 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Comanda {comanda.comanda} já está fechada")
            if comanda.status == 2:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Comanda {comanda.comanda} está cancelada e não pode ser recebida")

        # Validar se alguma comanda já está vinculada a outro recebimento
        result = await db.execute(
            select(RecebimentoComandaDB).where(RecebimentoComandaDB.comanda_id.in_(recebimento_data.comandas_ids))
        )
        ja_recebidas = result.scalars().all()
        if ja_recebidas:
            ids_ja_recebidas = [r.comanda_id for r in ja_recebidas]
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Comanda(s) já recebida(s) anteriormente: {ids_ja_recebidas}")

        # Validar funcionário responsável pelo recebimento
        result = await db.execute(select(FuncionarioDB).where(FuncionarioDB.id == recebimento_data.funcionario_id))
        funcionario = result.scalar_one_or_none()
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Funcionário não encontrado")

        # Validar cliente, se informado
        cliente = None
        if recebimento_data.cliente_id:
            result = await db.execute(select(ClienteDB).where(ClienteDB.id == recebimento_data.cliente_id))
            cliente = result.scalar_one_or_none()
            if not cliente:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente não encontrado")

        # Calcular subtotal de cada comanda (sempre no servidor, nunca confiando em valor externo)
        comandas_pagas_response = []
        subtotal_geral = 0.0

        for comanda in comandas:
            itens = await _montar_itens_comanda(db, comanda.id)
            total_comanda = sum(float(item.valor_unitario) * item.quantidade for item in itens)
            subtotal_geral += total_comanda

            comandas_pagas_response.append(ComandaPagaResponse(
                id=comanda.id,
                comanda=comanda.comanda,
                total=round(total_comanda, 2),
                quantidade_produtos=sum(item.quantidade for item in itens)
            ))

        desconto_total = recebimento_data.desconto_valor or 0
        acrescimo_total = recebimento_data.acrescimo_valor or 0
        valor_final = subtotal_geral - desconto_total + acrescimo_total

        if valor_final < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O desconto informado é maior que o valor total das comandas")

        # Criar o recebimento (cabeçalho)
        data_hora_recebimento = datetime.now()
        new_recebimento = RecebimentoDB(
            cliente_id=recebimento_data.cliente_id,
            funcionario_id=recebimento_data.funcionario_id,
            data_hora=data_hora_recebimento,
            subtotal_geral=round(subtotal_geral, 2),
            desconto_total=round(desconto_total, 2),
            acrescimo_total=round(acrescimo_total, 2),
            valor_final=round(valor_final, 2)
        )
        db.add(new_recebimento)
        await db.flush()  # garante new_recebimento.id disponível sem commit ainda

        # Vincular cada comanda ao recebimento e atualizar status/cliente/funcionário
        for comanda in comandas:
            db.add(RecebimentoComandaDB(recebimento_id=new_recebimento.id, comanda_id=comanda.id))

            comanda.status = 1  # fechada
            comanda.funcionario_id = recebimento_data.funcionario_id  # funcionário que recebeu
            if recebimento_data.cliente_id:
                comanda.cliente_id = recebimento_data.cliente_id

        # Commit único — se algo falhar antes daqui, nada é persistido (atomicidade real)
        await db.commit()
        await db.refresh(new_recebimento)

        # Registrar auditoria
        AuditoriaService.registrar_acao(
            db=db, funcionario_id=current_user.id, acao="CREATE", recurso="RECEBIMENTO",
            recurso_id=new_recebimento.id, dados_novos=new_recebimento, request=request
        )

        return RecebimentoCompletoResponse(
            sucesso=True,
            mensagem=f"Recebimento realizado com sucesso. {len(comandas)} comanda(s) quitada(s).",
            recebimento_id=new_recebimento.id,
            comandas_pagas=comandas_pagas_response,
            subtotal_geral=float(new_recebimento.subtotal_geral),
            desconto_total=float(new_recebimento.desconto_total),
            acrescimo_total=float(new_recebimento.acrescimo_total),
            valor_final=float(new_recebimento.valor_final),
            cliente=_cliente_to_response(cliente) if cliente else None,
            funcionario=_funcionario_to_response(funcionario),
            data_hora=new_recebimento.data_hora
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao processar recebimento: {str(e)}")


# ── 4. Gerar comprovante de um recebimento já realizado ──────────────────────
@router.get(
    "/recebimento/comprovante/{recebimento_id}",
    response_model=ComprovanteRecebimento,
    tags=["Recebimento"],
    summary="Gerar comprovante de recebimento - protegida por JWT e grupo 1 ou 3"
)
@limiter.limit("moderate")
async def get_comprovante(
    recebimento_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    try:
        # Buscar recebimento + funcionário + cliente
        query = (
            select(RecebimentoDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == RecebimentoDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == RecebimentoDB.cliente_id)
            .where(RecebimentoDB.id == recebimento_id)
        )
        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recebimento não encontrado")

        recebimento, funcionario, cliente = row

        # Buscar comandas vinculadas a esse recebimento
        result = await db.execute(
            select(RecebimentoComandaDB).where(RecebimentoComandaDB.recebimento_id == recebimento_id)
        )
        vinculos = result.scalars().all()

        comandas_comprovante = []
        for vinculo in vinculos:
            result = await db.execute(select(ComandaDB).where(ComandaDB.id == vinculo.comanda_id))
            comanda = result.scalar_one_or_none()
            if not comanda:
                continue

            itens = await _montar_itens_comanda(db, comanda.id)
            total_comanda = sum(float(item.valor_unitario) * item.quantidade for item in itens)

            comandas_comprovante.append(ComprovanteComandaItem(
                comanda=comanda.comanda,
                itens=itens,
                total=round(total_comanda, 2)
            ))

        return ComprovanteRecebimento(
            cabecalho=ComprovanteCabecalho(recebimento_id=recebimento.id),
            cliente=_cliente_to_response(cliente) if cliente else None,
            funcionario=_funcionario_to_response(funcionario),
            comandas=comandas_comprovante,
            resumo_valores=ComprovanteResumoValores(
                subtotal_geral=float(recebimento.subtotal_geral),
                desconto_total=float(recebimento.desconto_total),
                acrescimo_total=float(recebimento.acrescimo_total),
                valor_final=float(recebimento.valor_final)
            ),
            recebimento=ComprovanteRecebimentoInfo(id=recebimento.id, data_hora=recebimento.data_hora),
            rodape=ComprovanteRodape(),
            data_emissao=datetime.now()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao gerar comprovante: {str(e)}")