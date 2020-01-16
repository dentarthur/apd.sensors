import enum
import importlib
import sys
import pkg_resources
import traceback
import typing as t

import click

from .sensors import Sensor
from .exceptions import DataCollectionError, UserFacingCLIError


class ReturnCodes(enum.IntEnum):
    OK = 0
    BAD_SENSOR_PATH = 17


def get_sensor_by_path(sensor_path):
    try:
        module_name, sensor_name = sensor_path.split(":")
    except ValueError as err:
        raise UserFacingCLIError(
            "Sensor path must be in the format dotted.path.to.module:ClassName",
            return_code=ReturnCodes.BAD_SENSOR_PATH,
        ) from err
    try:
        module = importlib.import_module(module_name)
    except ImportError as err:
        raise UserFacingCLIError(
            f"Could not import module {module_name}",
            return_code=ReturnCodes.BAD_SENSOR_PATH,
        ) from err
    try:
        sensor_class = getattr(module, sensor_name)
    except AttributeError as err:
        raise UserFacingCLIError(
            f"Could not find attribute {sensor_name} in {module_name}",
            return_code=ReturnCodes.BAD_SENSOR_PATH,
        ) from err
    if (
        isinstance(sensor_class, type)
        and issubclass(sensor_class, Sensor)
        and sensor_class != Sensor
    ):
        return sensor_class()
    else:
        raise UserFacingCLIError(
            f"Detected object {sensor_class!r} is not recognised as a Sensor type",
            return_code=ReturnCodes.BAD_SENSOR_PATH,
        )


def get_sensors():
    sensors = []
    for sensor_class in pkg_resources.iter_entry_points("apd.sensors.sensors"):
        class_ = sensor_class.load()
        sensors.append(t.cast(Sensor[t.Any], class_()))
    return sensors


@click.command(help="Displays the values of the sensors")
@click.option(
    "--develop", required=False, metavar="path", help="Load a sensor by Python path"
)
@click.option("--verbose", is_flag=True, help="Show additional info")
def show_sensors(develop, verbose):
    sensors: t.Iterable[Sensor[t.Any]]
    if develop:
        try:
            sensors = [get_sensor_by_path(develop)]
        except UserFacingCLIError as error:
            if verbose:
                tb = traceback.format_exception(type(error), error, error.__traceback__)
                click.echo("".join(tb))
            click.secho(error.message, fg="red", bold=True)
            sys.exit(error.return_code)
    else:
        sensors = get_sensors()
    for sensor in sensors:
        click.secho(sensor.title, bold=True)
        try:
            click.echo(str(sensor))
        except DataCollectionError as error:
            if verbose:
                tb = traceback.format_exception(type(error), error, error.__traceback__)
                click.echo("".join(tb))
                continue
            click.echo(error)
        click.echo("")
    sys.exit(ReturnCodes.OK)


if __name__ == "__main__":
    show_sensors()
