# Felipe Bueno de Oliveira

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from infra.rate_limit import limiter, get_rate_limit
from services.AuditoriaService import AuditoriaService

from domain.schemas.ProdutoSchema import (
    ProdutoCreate,
    ProdutoUpdate,
    ProdutoResponse
)

from domain.schemas.AuthSchema import FuncionarioAuth
from infra.orm.ProdutoModel import ProdutoDB
from infra.database import get_async_db
from infra.dependencies import get_current_active_user, require_group

router = APIRouter()


# 🔓 Público (sem id e valor)
@router.get("/produto/publico", tags=["Produto"], status_code=status.HTTP_200_OK)
@limiter.limit(get_rate_limit("Critical"))
async def get_produtos_publico(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        result = await db.execute(select(ProdutoDB))
        produtos = result.scalars().all()

        return [
            {
                "nome": produto.nome,
                "descricao": produto.descricao,
                "foto": produto.foto
            }
            for produto in produtos
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produtos públicos: {str(e)}"
        )


# 🔒 Listar todos
@router.get(
    "/produto/",
    response_model=List[ProdutoResponse],
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("Critical"))
async def get_produtos(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(select(ProdutoDB))
        produtos = result.scalars().all()

        return produtos

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produtos: {str(e)}"
        )


# 🔒 Buscar por ID
@router.get(
    "/produto/{id}",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("Critical"))
async def get_produto(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(
            select(ProdutoDB).where(ProdutoDB.id == id)
        )
        produto = result.scalar_one_or_none()

        if not produto:
            raise HTTPException(
                status_code=404,
                detail="Produto não encontrado"
            )

        return produto

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produto: {str(e)}"
        )


# 🔒 Criar
@router.post(
    "/produto/",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_201_CREATED
)
@limiter.limit(get_rate_limit("Critical"))
async def post_produto(
    request: Request,
    produto_data: ProdutoCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        novo_produto = ProdutoDB(
            nome=produto_data.nome,
            descricao=produto_data.descricao,
            foto=produto_data.foto,
            valor_unitario=produto_data.valor_unitario
        )

        db.add(novo_produto)
        await db.commit()
        await db.refresh(novo_produto)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="PRODUTO",
            recurso_id=novo_produto.id,
            dados_novos=novo_produto,
            request=request
        )

        return novo_produto

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar produto: {str(e)}"
        )


# 🔒 Atualizar
@router.put(
    "/produto/{id}",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("Critical"))
async def put_produto(
    request: Request,
    id: int,
    produto_data: ProdutoUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        result = await db.execute(
            select(ProdutoDB).where(ProdutoDB.id == id)
        )
        produto = result.scalar_one_or_none()

        if not produto:
            raise HTTPException(
                status_code=404,
                detail="Produto não encontrado"
            )

        dados_antigos_obj = produto.__dict__.copy()

        update_data = produto_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(produto, field, value)

        await db.commit()
        await db.refresh(produto)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="PRODUTO",
            recurso_id=produto.id,
            dados_antigos=dados_antigos_obj,
            dados_novos=produto,
            request=request
        )

        return produto

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar produto: {str(e)}"
        )


# 🔒 Deletar
@router.delete(
    "/produto/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Produto"]
)
@limiter.limit(get_rate_limit("Critical"))
async def delete_produto(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        result = await db.execute(
            select(ProdutoDB).where(ProdutoDB.id == id)
        )
        produto = result.scalar_one_or_none()

        if not produto:
            raise HTTPException(
                status_code=404,
                detail="Produto não encontrado"
            )

        await db.delete(produto)
        await db.commit()

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="PRODUTO",
            recurso_id=id,
            dados_antigos=produto,
            request=request
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao deletar produto: {str(e)}"
        )