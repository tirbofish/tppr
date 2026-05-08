import logging


class TPPRPackageLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("tppr_paper_utils")


def pytest_configure(config):
    # logging support
    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")
    if not logging_plugin:
        return

    package_filter = TPPRPackageLogFilter()
    logging_plugin.log_cli_handler.addFilter(package_filter)


def pytest_runtest_setup(item):
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger("tppr_paper_utils").setLevel(logging.DEBUG)

    logging_plugin = item.config.pluginmanager.get_plugin("logging-plugin")
    if logging_plugin:
        logging_plugin.log_cli_handler.setLevel(logging.DEBUG)
    logging_plugin.log_cli_handler.setLevel(logging.DEBUG)
