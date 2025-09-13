"""
ICGS Exceptions - Gestion erreurs et limitations système
"""

class ICGSException(Exception):
    """Base exception pour système ICGS"""
    def __init__(self, message: str, error_code: str = "ICGS_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class PathEnumerationNotReadyError(ICGSException):
    """
    Exception pour limitations Path Enumeration en développement
    
    Utilisée pour documenter fonctionnalités en cours d'implémentation
    dans PHASE 2.9 - Intégration Path-NFA + Pipeline Complet
    """
    def __init__(self, message: str, error_code: str = "PATH_ENUM_PENDING"):
        super().__init__(message, error_code)


class IntegrationLimitationError(ICGSException):
    """
    Exception pour limitations intégration pipeline ICGS
    
    Utilisée pour documenter composants isolés fonctionnels
    mais intégration inter-composants en développement
    """
    def __init__(self, message: str, error_code: str = "INTEGRATION_PENDING"):
        super().__init__(message, error_code)


class TaxonomyMappingError(ICGSException):
    """Exception pour erreurs mapping taxonomie"""
    def __init__(self, message: str, error_code: str = "TAXONOMY_ERROR"):
        super().__init__(message, error_code)


class DAGValidationError(ICGSException):
    """Exception pour erreurs validation DAG"""
    def __init__(self, message: str, error_code: str = "DAG_VALIDATION_ERROR"):
        super().__init__(message, error_code)