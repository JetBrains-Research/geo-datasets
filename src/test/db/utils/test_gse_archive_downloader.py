import asyncio
import errno
from unittest import TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from parameterized import parameterized

from src.config.config import Config
from src.db.utils.gse_archive_downloader import GSEArchiveDownloader
from src.exception.disk_space_error import DiskSpaceError


class TestGseArchiveDownloader(TestCase):
    def setUp(self):
        config = Config(test=True)

        session = MagicMock()
        session.get = MagicMock(return_value=AsyncMock())

        self.gse_archive_downloader = GSEArchiveDownloader(
            config=config,
            session=session,
            dont_redownload=False,
        )

    @parameterized.expand([
        # accession longer than 6 chars — replace last 3 digits with 'nnn'
        ("GSE1234", "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE1nnn/GSE1234/soft/GSE1234_family.soft.gz"),
        ("GSE12345", "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE12nnn/GSE12345/soft/GSE12345_family.soft.gz"),
        ("GSE123456", "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE123nnn/GSE123456/soft/GSE123456_family.soft.gz"),
        # accession exactly 6 chars — uses "GSEnnn" as batch prefix
        ("GSE123", "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE123/soft/GSE123_family.soft.gz"),
        # accession shorter than 6 chars — uses "GSEnnn" as batch prefix
        ("GSE38", "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE38/soft/GSE38_family.soft.gz"),
        ("GSE1", "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE1/soft/GSE1_family.soft.gz"),
    ])
    def test_get_download_url(self, accession: str, expected_url: str):
        self.assertEqual(GSEArchiveDownloader.get_download_url(accession), expected_url)

    def test_download_gzip_converts_no_space_error(self):
        download_path = "/tmp/GSE1234.soft.gz"
        response = MagicMock()

        async def chunks():
            yield b"archive chunk"

        response.content.iter_chunked.return_value = chunks()
        response_context = MagicMock()
        response_context.__aenter__ = AsyncMock(return_value=response)
        response_context.__aexit__ = AsyncMock(return_value=None)
        self.gse_archive_downloader.session.get = MagicMock(return_value=response_context)

        archive = MagicMock()
        archive.write = AsyncMock(side_effect=OSError(errno.ENOSPC, "No space left on device"))
        archive_context = MagicMock()
        archive_context.__aenter__ = AsyncMock(return_value=archive)
        archive_context.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.db.utils.gse_archive_downloader.aiofiles.open", return_value=archive_context),
            patch(
                "src.db.utils.gse_archive_downloader.async_remove_if_exists",
                new_callable=AsyncMock,
            ) as remove_archive,
        ):
            with self.assertRaises(DiskSpaceError):
                asyncio.run(self.gse_archive_downloader.download_gzip(download_path, "https://example.test/archive.gz"))

        remove_archive.assert_awaited_once_with(download_path)
