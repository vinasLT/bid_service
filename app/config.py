from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Permissions(str, Enum):
    BID_WRITE = "bid.own:write"
    BID_READ = "bid.own:read"

    BID_ALL_READ = "bid.all:read"
    BID_ALL_WRITE = "bid.all:write"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "bid-service"
    DEBUG: bool = True
    ROOT_PATH: str = ''
    ENVIRONMENT: Environment = Environment.DEVELOPMENT

    @property
    def enable_docs(self) -> bool:
        return self.ENVIRONMENT in [Environment.DEVELOPMENT]

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "test_db"
    DB_USER: str = "postgres"
    DB_PASS: str = "testpass"

    # rabbitmq
    RABBITMQ_URL: str = 'amqp://guest:guest@localhost:5672/'
    RABBITMQ_EXCHANGE_NAME: str = 'events'

    # rpc
    RPC_API_URL: str = "localhost:50051"
    RPC_PAYMENT_URL: str = "localhost:50053"
    RPC_AUTH_URL: str = "localhost:50054"
    RPC_CALCULATOR_URL: str = "localhost:50052"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
