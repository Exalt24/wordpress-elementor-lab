<?php
namespace Opencart\Catalog\Controller\Extension\Seolab\Event;

require_once DIR_EXTENSION . 'seolab/system/library/markup.php';

use Seolab\Markup;

/**
 * Technical SEO fixes for a stock OpenCart 4 storefront, wired in as events (see scripts/events.sql)
 * so no core file is edited and removing the event rows removes the whole change.
 */
class Seo extends \Opencart\System\Engine\Controller {
	private const NOINDEX_ROUTES = ['product/search', 'product/compare', 'checkout/cart', 'checkout/checkout', 'account/login', 'account/register', 'account/account'];

	/** controller/common/header/before: bring the title to 30 to 65 characters and fill an empty meta description from the page text, so the header prints both. */
	public function head(string &$route, array &$args): void {
		$this->document->setTitle(Markup::pageTitle($this->document->getTitle(), (string)$this->config->get('config_name')));

		if ($this->document->getDescription() !== '') {
			return;
		}

		$page = $this->current();

		if ($page && $page['description'] !== '') {
			$this->document->setDescription(Markup::metaDescription($page['description']));
		}
	}

	/** view/common/header/after: add the canonical link, robots, Open Graph tags and JSON-LD to the head, only where missing. */
	public function markup(string &$route, array &$data, string &$output): void {
		$request_route = $this->request->get['route'] ?? 'common/home';
		$base = $this->config->get('config_url');
		$name = (string)$this->config->get('config_name');
		$page = $this->current();
		$extra = '';

		if (stripos($output, 'rel="canonical"') === false) {
			$extra .= '<link href="' . ($page['canonical'] ?? $base) . '" rel="canonical"/>' . "\n";
		}

		if (in_array($request_route, self::NOINDEX_ROUTES, true)) {
			$extra .= '<meta name="robots" content="noindex,follow"/>' . "\n";
		}

		$title = $this->document->getTitle();
		$description = $this->document->getDescription() ?: ($page['description'] ?? '');
		$extra .= Markup::openGraph($title, Markup::metaDescription($description), $page['og_type'] ?? 'website', $page['canonical'] ?? $base, $page['image'] ?? '');

		$graph = [];

		if ($request_route === 'common/home') {
			$graph[] = Markup::organization($name, $base);
			$graph[] = Markup::website($name, $base);
		} elseif ($page && !empty($page['crumbs'])) {
			$graph[] = Markup::breadcrumbs($page['crumbs']);
		}

		if ($page && isset($page['product'])) {
			$graph[] = Markup::product($page['product']);
		}

		if ($graph) {
			$extra .= Markup::jsonLd($graph) . "\n";
		}

		$output = Markup::injectIntoHead($output, $extra);
	}

	/** view/product/thumb/after: the product card title is an h4 straight under the page h1, so it becomes an h2 styled as an h4. */
	public function thumb(string &$route, array &$data, string &$output): void {
		$output = Markup::retagHeading($output, 4, 2);
	}

	/** view/extension/opencart/module/featured/after: the module title is an h3 straight under the home h1, so it becomes an h2 styled as an h3. */
	public function featured(string &$route, array &$data, string &$output): void {
		$output = Markup::retagHeading($output, 3, 2);
	}

	/** view/common/footer/after: the footer column titles are h5, which skips four levels, so they become h2 styled as an h5. */
	public function footer(string &$route, array &$data, string &$output): void {
		$output = Markup::retagHeading($output, 5, 2);
	}

	/** view/common/home/before: swap in the home template that has an h1, an intro and links into the catalogue. */
	public function home(string &$route, array &$data, string &$code, string &$output): void {
		$this->load->model('catalog/category');

		$data['heading'] = (string)$this->config->get('config_meta_title') ?: (string)$this->config->get('config_name');
		$data['intro'] = (string)$this->config->get('config_meta_description');
		$data['categories'] = [];

		foreach ($this->model_catalog_category->getCategories(0) as $category) {
			$data['categories'][] = ['name' => $category['name'], 'href' => $this->url->link('product/category', 'language=' . $this->config->get('config_language') . '&path=' . $category['category_id'])];
		}

		$route = 'extension/seolab/common/home';
	}

	/** What this request is: its canonical address, description, crumbs and, for a product, the product data. Null on pages with nothing to add. */
	private function current(): ?array {
		$route = $this->request->get['route'] ?? 'common/home';
		$language = 'language=' . $this->config->get('config_language');
		$home = $this->config->get('config_url');

		if ($route === 'product/product' && !empty($this->request->get['product_id'])) {
			$this->load->model('catalog/product');
			$p = $this->model_catalog_product->getProduct((int)$this->request->get['product_id']);

			if (!$p) {
				return null;
			}

			$url = Markup::canonicalUrl($this->url->link('product/product', $language . '&product_id=' . (int)$p['product_id']));
			$image = $p['image'] ? $home . 'image/' . $p['image'] : '';
			$crumbs = [['Home', $home]];

			if (!empty($this->request->get['path'])) {
				$ids = explode('_', (string)$this->request->get['path']);
				$this->load->model('catalog/category');
				$category = $this->model_catalog_category->getCategory((int)end($ids));

				if ($category) {
					$crumbs[] = [$category['name'], Markup::canonicalUrl($this->url->link('product/category', $language . '&path=' . (int)$category['category_id']))];
				}
			}

			$crumbs[] = [$p['name'], ''];

			return [
				'canonical'   => $url,
				'description' => $p['meta_description'] ?: strip_tags(html_entity_decode($p['description'], ENT_QUOTES, 'UTF-8')),
				'og_type'     => 'product',
				'image'       => $image,
				'crumbs'      => $crumbs,
				'product'     => ['name' => $p['name'], 'description' => $p['description'], 'url' => $url, 'price' => $p['special'] ?: $p['price'], 'currency' => $this->config->get('config_currency'), 'quantity' => $p['quantity'], 'image' => $image, 'model' => $p['model']]
			];
		}

		if ($route === 'product/category' && !empty($this->request->get['path'])) {
			$ids = explode('_', (string)$this->request->get['path']);
			$this->load->model('catalog/category');
			$category = $this->model_catalog_category->getCategory((int)end($ids));

			if (!$category) {
				return null;
			}

			$url = Markup::canonicalUrl($this->url->link('product/category', $language . '&path=' . (int)$category['category_id'] . (isset($this->request->get['page']) ? '&page=' . (int)$this->request->get['page'] : '')));

			return [
				'canonical'   => $url,
				'description' => $category['meta_description'] ?: strip_tags(html_entity_decode($category['description'], ENT_QUOTES, 'UTF-8')),
				'og_type'     => 'website',
				'image'       => $category['image'] ? $home . 'image/' . $category['image'] : '',
				'crumbs'      => [['Home', $home], [$category['name'], '']]
			];
		}

		if ($route === 'common/home') {
			return ['canonical' => $home, 'description' => (string)$this->config->get('config_meta_description'), 'og_type' => 'website'];
		}

		return null;
	}
}
