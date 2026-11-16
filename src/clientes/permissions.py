def filtrar_por_cliente(queryset, usuario, campo):
    """Devuelve todo al staff; al cliente, solo lo que le pertenece.

    `campo` es el nombre del campo que apunta al Cliente en ese modelo
    (por ejemplo "cliente" en Pedido, Alquiler o Turno).
    """
    if usuario.is_staff:
        return queryset

    cliente = getattr(usuario, "cliente", None)
    if cliente is None:
        return queryset.none()

    return queryset.filter(**{campo: cliente})