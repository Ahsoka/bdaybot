from arsenic.errors import ArsenicTimeout, NoSuchElement

class FailedToAddToCart(Exception):
    pass

class IncorrectCartValue(Exception):
    pass

class AddressNotFoundError(Exception):
    pass

class NoAvailableDelivery(Exception):
    pass
